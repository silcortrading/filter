import os
import pandas as pd
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, redirect, url_for, flash
import xml.dom.minidom
import glob
from werkzeug.utils import secure_filename
import time
import logging
import re
from flask import send_from_directory

# Configuração da aplicação Flask
app = Flask(__name__)

# Diretórios e extensões permitidas
UPLOAD_FOLDER = 'UPLOADS'
DOWNLOAD_FOLDER = 'downloads'
CONV_XML_XML = 'conv_XML_XML'
CONV_EXCEL_XML = 'conv_EXCEL_XML'
ALLOWED_EXTENSIONS = {'xlsx', 'xml'}

# Criar pastas necessárias
for folder in [UPLOAD_FOLDER, CONV_XML_XML, CONV_EXCEL_XML]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONV_EXCEL_XML'] = CONV_EXCEL_XML
app.config['CONV_XML_XML'] = CONV_XML_XML
app.secret_key = os.getenv('SECRET_KEY', 'default_key')

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Funções auxiliares
def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_next_filename(directory, prefix):
    """Retorna o próximo número disponível para nomear um arquivo."""
    existing_files = glob.glob(os.path.join(directory, f"{prefix}_*.xml"))
    numbers = [int(file.split("_")[-1].split(".")[0]) for file in existing_files]
    return max(numbers) + 1 if numbers else 1

def save_pretty_xml(root, filepath):
    """Salva um arquivo XML formatado."""
    dom = xml.dom.minidom.parseString(ET.tostring(root, 'utf-8'))
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(dom.toprettyxml())

def extract_lote(descricao):
    """Extrai o valor do lote a partir de uma descrição."""
    match = re.search(r'LOTE:\s*(\w+)', str(descricao))
    return match.group(1) if match else None

# Conversão de Excel para XML
def convert_excel_to_xml(filepath):
    df = pd.read_excel(filepath, header=None)
    selected_columns = df.iloc[:, [0, 3]].copy()
    selected_columns.columns = ['quantidade', 'descricaoMercadoria']

    selected_columns.sort_values(by=['descricaoMercadoria'], inplace=True)

    root = ET.Element("Root")
    for item_number, (_, row) in enumerate(selected_columns.iterrows(), start=1):
        item_element = ET.SubElement(root, f"item{item_number}")
        for column in selected_columns.columns:
            # Substituindo espaços duplos por um único no campo descricaoMercadoria
            if column == 'descricaoMercadoria':
                descricao_text = str(row[column]).strip() if pd.notnull(row[column]) else ''
                descricao_text = re.sub(r'\s{1,}', '', descricao_text)  # Substitui múltiplos espaços por um único
                ET.SubElement(item_element, column).text = descricao_text
            else:
                ET.SubElement(item_element, column).text = str(row[column]) if pd.notnull(row[column]) else ''

        lote_value = extract_lote(row['descricaoMercadoria'])
        if lote_value:
            ET.SubElement(item_element, "lote").text = lote_value

    xml_filename = f"XML_CONVERTIDO_EXCEL_{get_next_filename(CONV_EXCEL_XML, 'XML_CONVERTIDO_EXCEL')}.xml"
    save_pretty_xml(root, os.path.join(CONV_EXCEL_XML, xml_filename))
    return xml_filename

# Filtragem de XML
def filter_xml_and_generate_new(input_filepath):
    tree = ET.parse(input_filepath)
    root = tree.getroot()

    new_root = ET.Element("Root")
    items = []

    for adicao in root.findall(".//adicao"):
        descricao_list = adicao.findall(".//descricaoMercadoria")
        quantidade_list = adicao.findall(".//quantidade")

        for descricao, quantidade in zip(descricao_list, quantidade_list):
            item_element = ET.Element("item")

            quantidade_text = quantidade.text.lstrip('0') if quantidade is not None else '0'
            try:
                quantidade_value = int(quantidade_text) / 100000
                quantidade_text = f"{quantidade_value:.0f}"
            except ValueError:
                quantidade_text = '0'

            # Substituindo espaços duplos por um único espaço
            descricao_text = descricao.text.strip() if descricao is not None else ''
            descricao_text = re.sub(r'\s{1,}', '', descricao_text)  # Substitui múltiplos espaços por um único

            ET.SubElement(item_element, "quantidade").text = quantidade_text
            ET.SubElement(item_element, "descricaoMercadoria").text = descricao_text

            lote_value = extract_lote(descricao.text)
            if lote_value:
                ET.SubElement(item_element, "lote").text = lote_value

            items.append(item_element)

    items.sort(key=lambda x: x.find("descricaoMercadoria").text.lower())
    for idx, item in enumerate(items, start=1):
        item.tag = f"item{idx}"
        new_root.append(item)

    xml_filename = f"XML_CONVERTIDO_XML_{get_next_filename(CONV_XML_XML, 'XML_CONVERTIDO_XML')}.xml"
    save_pretty_xml(new_root, os.path.join(CONV_XML_XML, xml_filename))
    return xml_filename

# Rotas
@app.route('/excel', methods=['GET', 'POST'])
def upload_excel_file():
    if request.method == 'POST':
        file = request.files.get('file')

        if not file or not allowed_file(file.filename):
            flash('Arquivo inválido ou não selecionado.')
            return redirect(request.url)

        filepath = os.path.join(UPLOAD_FOLDER, f"{int(time.time())}_{secure_filename(file.filename)}")
        file.save(filepath)

        try:
            xml_filename = convert_excel_to_xml(filepath)
            flash('Arquivo Excel convertido com sucesso!')
            # Redireciona após o sucesso
            return redirect(url_for('upload_excel_file', xml_filename=xml_filename))
        except Exception as e:
            logger.error(f"Erro ao converter Excel: {e}")
            flash(f"Erro ao converter o arquivo Excel: {e}")

    # Exibe o resultado, se disponível
    xml_filename = request.args.get('xml_filename')
    return render_template('index.html', xml_filename=xml_filename)

@app.route('/', methods=['GET', 'POST'])
def upload_xml_file():
    if request.method == 'POST':
        file = request.files.get('file')

        if not file or not allowed_file(file.filename):
            flash('Arquivo inválido ou não selecionado.')
            return redirect(request.url)

        filepath = os.path.join(UPLOAD_FOLDER, f"{int(time.time())}_{secure_filename(file.filename)}")
        file.save(filepath)

        try:
            filtered_xml_filename = filter_xml_and_generate_new(filepath)
            flash('Arquivo XML filtrado com sucesso!')
            # Redireciona após o sucesso
            return redirect(url_for('upload_xml_file', filtered_xml_filename=filtered_xml_filename))
        except Exception as e:
            logger.error(f"Erro ao filtrar XML: {e}")
            flash(f"Erro ao filtrar o arquivo XML: {e}")

    # Exibe o resultado, se disponível
    filtered_xml_filename = request.args.get('filtered_xml_filename')
    return render_template('index.html', filtered_xml_filename=filtered_xml_filename)

@app.route('/clear_files', methods=['POST'])
def clear_files():
    try:
        for folder in [CONV_XML_XML, CONV_EXCEL_XML, UPLOAD_FOLDER]:
            for file in glob.glob(os.path.join(folder, '*')):
                os.remove(file)

        flash('Arquivos removidos com sucesso!')
    except Exception as e:
        logger.error(f"Erro ao limpar arquivos: {e}")
        flash(f"Erro ao limpar as pastas: {e}")

    return redirect(url_for('upload_xml_file')) 

@app.route('/download/<folder>/<filename>')
def download_file(folder, filename):
    # Assuming the 'folder' is one of the folders where files are stored
    return send_from_directory(f'./{folder}', filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False)  