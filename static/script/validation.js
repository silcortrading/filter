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