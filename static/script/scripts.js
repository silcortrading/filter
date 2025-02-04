document.getElementById('excelForm').addEventListener('submit', function (event) {
  const fileInput = document.getElementById('excelFile');
  const file = fileInput.files[0];
  if (!file || !['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'].includes(file.type)) {
      alert('Por favor, envie um arquivo Excel válido (.xls ou .xlsx).');
      event.preventDefault();
  }
});

document.getElementById('xmlForm').addEventListener('submit', function (event) {
  const fileInput = document.getElementById('xmlFile');
  const file = fileInput.files[0];
  if (!file || file.type !== 'text/xml') {
      alert('Por favor, envie um arquivo XML válido.');
      event.preventDefault();
  }
});

document.querySelectorAll('.list-header').forEach(header => {
  header.addEventListener('click', () => {
    const content = header.nextElementSibling;
    const arrow = header.querySelector('.arrow');

    // Verifica se o conteúdo já está expandido
    if (content.style.maxHeight) {
      // Recolhe o conteúdo
      content.style.maxHeight = null;
      content.style.paddingTop = 0;
      content.style.paddingBottom = 0;
      arrow.classList.remove('expanded');
    } else {
      // Recolhe outros itens abertos
      document.querySelectorAll('.list-content').forEach(otherContent => {
        if (otherContent !== content) {
          otherContent.style.maxHeight = null;
          otherContent.style.paddingTop = 0;
          otherContent.style.paddingBottom = 0;
          const otherArrow = otherContent.previousElementSibling.querySelector('.arrow');
          if (otherArrow) {
            otherArrow.classList.remove('expanded');
          }
        }
      });

      // Expande o conteúdo atual
      content.style.maxHeight = content.scrollHeight + "px";
      content.style.paddingTop = "20px";
      content.style.paddingBottom = "20px";
      arrow.classList.add('expanded');
    }
  });
});

// PING NO SERVIDOR
setInterval(function() {
  fetch('/ping', { method: 'GET' })
      .then(response => response.text())
      .then(data => console.log("Ping recebido", data));
}, 100000); 