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
RESULT_FOLDER = 'RESULT'
ALLOWED_EXTENSIONS = {'xlsx', 'xml'}

# Criar pastas necessárias
for folder in [UPLOAD_FOLDER, CONV_XML_XML, CONV_EXCEL_XML, RESULT_FOLDER]:
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

def format_descricao(descricao):
    """Formata a descrição removendo espaços extras."""
    return re.sub(r'\s{1,}', '', descricao.strip()) if descricao else ''

def convert_excel_to_xml(filepath):
    df = pd.read_excel(filepath, header=None)
    selected_columns = df.iloc[:, [0, 3]].copy()
    selected_columns.columns = ['quantidade', 'descricaoMercadoria']
    
    # Gera o XML
    root = ET.Element("Root")
    for item_number, (_, row) in enumerate(selected_columns.iterrows(), start=1):
        item_element = ET.SubElement(root, f"item{item_number}")
        
        quantidade = str(row['quantidade']) if pd.notnull(row['quantidade']) else '0'
        descricao = format_descricao(str(row['descricaoMercadoria'])) if pd.notnull(row['descricaoMercadoria']) else ''
        
        ET.SubElement(item_element, "quantidade").text = quantidade
        ET.SubElement(item_element, "descricaoMercadoria").text = descricao

        lote_value = extract_lote(descricao)
        if lote_value:
            ET.SubElement(item_element, "lote").text = lote_value
            
    xml_filename = f"XML_CONVERTIDO_EXCEL_{get_next_filename(CONV_EXCEL_XML, 'XML_CONVERTIDO_EXCEL')}.xml"
    save_pretty_xml(root, os.path.join(CONV_EXCEL_XML, xml_filename))
    
    # Criação da pasta RESULT caso não exista
    os.makedirs(RESULT_FOLDER, exist_ok=True)

    # Caminho do arquivo Excel na pasta RESULT
    result_filename = "result_excel_filter.xlsx"
    result_filepath = os.path.join(RESULT_FOLDER, result_filename)

    # Se o arquivo Excel já existir, carrega o existente para garantir a estrutura
    if os.path.exists(result_filepath):
        existing_df = pd.read_excel(result_filepath)
        
        # Garante que o dataframe tenha as colunas esperadas
        while existing_df.shape[1] < 5:
            existing_df.insert(existing_df.shape[1], f'Col{existing_df.shape[1] + 2}', '')

        # Insere os novos valores nas colunas A e B
        existing_df.iloc[:, 0] = selected_columns['quantidade']  # Coluna A
        existing_df.iloc[:, 1] = selected_columns['descricaoMercadoria']  # Coluna B
    else:
        # Se não existir, cria um novo DataFrame com colunas organizadas
        existing_df = pd.DataFrame({
            'A': selected_columns['quantidade'],
            'B': selected_columns['descricaoMercadoria'],
            'C': [''] * len(selected_columns),
            'D': [''] * len(selected_columns),
            'E': [''] * len(selected_columns)
        })

    # Salva o novo arquivo Excel com as colunas organizadas
    existing_df.to_excel(result_filepath, index=False)

    return xml_filename

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

            descricao_text = format_descricao(descricao.text) if descricao is not None else ''

            ET.SubElement(item_element, "quantidade").text = quantidade_text
            ET.SubElement(item_element, "descricaoMercadoria").text = descricao_text

            lote_value = extract_lote(descricao.text)
            if lote_value:
                ET.SubElement(item_element, "lote").text = lote_value

            items.append(item_element)

    # Renomeia os itens com base na nova ordem
    for idx, item in enumerate(items, start=1):
        item.tag = f"item{idx}"
        new_root.append(item)

    # Salva o XML filtrado
    xml_filename = f"XML_CONVERTIDO_XML_{get_next_filename(CONV_XML_XML, 'XML_CONVERTIDO_XML')}.xml"
    save_pretty_xml(new_root, os.path.join(CONV_XML_XML, xml_filename))

    # Criação da pasta RESULT caso não exista
    os.makedirs(RESULT_FOLDER, exist_ok=True)

    # Extrai dados do XML filtrado para adicionar no Excel
    filtered_data = []
    for item in items:
        quantidade = item.find('quantidade').text
        descricao = item.find('descricaoMercadoria').text
        filtered_data.append([quantidade, descricao])

    filtered_df = pd.DataFrame(filtered_data, columns=['quantidade', 'descricaoMercadoria'])

    # Caminho do arquivo Excel na pasta RESULT
    result_filename = f"result_excel_filter.xlsx"
    result_filepath = os.path.join(RESULT_FOLDER, result_filename)

    # Se o arquivo Excel já existir, carrega o existente para adicionar novas colunas corretamente
    if os.path.exists(result_filepath):
        existing_df = pd.read_excel(result_filepath)

        # Garante que o dataframe tenha as colunas esperadas
        while existing_df.shape[1] < 5:
            existing_df.insert(existing_df.shape[1], f'Col{existing_df.shape[1] + 2}', '')

        # Insere os novos valores nas colunas D e E
        existing_df.iloc[:, 3] = filtered_df['quantidade']  # Coluna D
        existing_df.iloc[:, 4] = filtered_df['descricaoMercadoria']  # Coluna E
    else:
        # Se não existir, cria um novo DataFrame com colunas A e B vazias, e D e E preenchidas
        existing_df = pd.DataFrame({
            'A': [''] * len(filtered_df),
            'B': [''] * len(filtered_df),
            'C': [''] * len(filtered_df),
            'D': filtered_df['quantidade'],
            'E': filtered_df['descricaoMercadoria']
        })

    # Salva o novo arquivo Excel com as colunas organizadas
    existing_df.to_excel(result_filepath, index=False)

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
            return redirect(url_for('upload_excel_file', xml_filename=xml_filename))
        except Exception as e:
            logger.error(f"Erro ao converter Excel: {e}")
            flash(f"Erro ao converter o arquivo Excel: {e}")

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
            return redirect(url_for('upload_xml_file', filtered_xml_filename=filtered_xml_filename))
        except Exception as e:
            logger.error(f"Erro ao filtrar XML: {e}")
            flash(f"Erro ao filtrar o arquivo XML: {e}")

    filtered_xml_filename = request.args.get('filtered_xml_filename')
    return render_template('index.html', filtered_xml_filename=filtered_xml_filename)

@app.route('/clear_files', methods=['POST'])
def clear_files():
    try:
        for folder in [CONV_XML_XML, CONV_EXCEL_XML, UPLOAD_FOLDER, RESULT_FOLDER]:
            for file in glob.glob(os.path.join(folder, '*')):
                os.remove(file)

        flash('Arquivos removidos com sucesso!')
    except Exception as e:
        logger.error(f"Erro ao limpar arquivos: {e}")
        flash(f"Erro ao limpar as pastas: {e}")

    return redirect(url_for('upload_xml_file')) 

@app.route('/download/<folder>/<filename>')
def download_file(folder, filename):
    return send_from_directory(f'./{folder}', filename, as_attachment=True)

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

@app.route("/ping")
def ping():
    return "pong"

@app.route('/download_excel')
def download_excel():
    result_filepath = os.path.join(RESULT_FOLDER, "result_excel_filter.xlsx")
    if os.path.exists(result_filepath):
        return send_from_directory(RESULT_FOLDER, "result_excel_filter.xlsx", as_attachment=True)
    else:
        flash("Arquivo Excel não encontrado.", "error")
        return redirect(request.referrer)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))