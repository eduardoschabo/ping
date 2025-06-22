from flask import Flask, render_template_string, request, session, jsonify, redirect, send_file
from ping3 import ping
import psutil
import json
import os

app = Flask(__name__)
app.secret_key = 'chave-super-secreta'

DATA_FILE = 'ips_monitorados.json'

def carregar_ips():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def salvar_ips():
    with open(DATA_FILE, 'w') as f:
        json.dump(ips_monitorados, f)

ips_monitorados = carregar_ips()
ips_status = {}

template = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Dashboard Provedor</title>
  <style>
    body {
      margin: 0;
      font-family: 'Segoe UI', sans-serif;
      background: #f4f7fa;
      color: #333;
    }
    header {
      background: #2563eb;
      color: white;
      padding: 1rem;
      font-size: 1.5rem;
      text-align: center;
    }
    main {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      padding: 1rem;
      justify-content: center;
    }
    .card {
      background: white;
      padding: 1rem;
      border-radius: 12px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.1);
      flex: 1 1 300px;
      max-width: 400px;
    }
    #form-add-ip, #form-import {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }
    #form-add-ip input, #form-import input[type="file"] {
      padding: 0.5rem;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 1rem;
    }
    #form-add-ip button, #form-import button {
      padding: 0.5rem;
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
    }
    ul#ips-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    #ips-list li {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem;
      border-bottom: 1px solid #ddd;
      gap: 0.5rem;
    }
    .ip-text {
      flex-grow: 1;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.4rem;
    }
    .ip-name, .ip-address {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .ip-name {
      font-weight: 700;
      color: #2563eb;
    }
    .status-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
      animation: pulse 1.5s infinite ease-in-out;
    }
    .online { background-color: #22c55e; }
    .offline { background-color: #ef4444; }
    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 0.9; }
      50% { transform: scale(1.4); opacity: 0.5; }
    }
    .btn-ip {
      font-size: 0.85rem;
      padding: 0.25rem 0.5rem;
      border: none;
      background: #2563eb;
      color: white;
      border-radius: 4px;
      cursor: pointer;
    }
    .btn-delete {
      background: #ef4444;
    }
    .modal {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10;
      display: none;
    }
    .modal.active {
      display: flex;
    }
    .modal-content {
      background: white;
      padding: 2rem;
      border-radius: 12px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2);
      width: 300px;
    }
    @media (max-width: 600px) {
      .card {
        flex: 1 1 100%;
        max-width: 100%;
      }
    }
  </style>
</head>
<body>
<header>Cloud Dashboard Provedor - Avançado</header>
<main>
  <section class="card">
    <h2>CPU</h2>
    <p id="cpu-usage">--%</p>
  </section>
  <section class="card">
    <h2>Internet</h2>
    <p id="internet-status">--</p>
  </section>
  <section class="card">
    <h2>Gerenciar IPs</h2>
    <form id="form-add-ip" method="POST">
      <input name="novo-nome" type="text" placeholder="Nome do IP" required>
      <input name="novo-ip" type="text" placeholder="Endereço IP" required>
      <button type="submit">Adicionar IP</button>
    </form>
    <form id="form-import" action="/importar" method="POST" enctype="multipart/form-data">
      <input type="file" name="arquivo" required>
      <button type="submit">Importar IPs</button>
    </form>
    <a href="/exportar" class="btn-ip">Exportar IPs</a>
    <h3 style="margin-top:1rem">IPs Monitorados</h3>
    <ul id="ips-list">
      {% for item in ips %}
      <li data-ip="{{ item.ip }}">
        <span class="ip-text">
          <span class="status-dot {% if ips_status[item.ip] %}online{% else %}offline{% endif %}"></span>
          <span class="ip-name">{{ item.nome }}</span>
          <span class="ip-address">{{ item.ip }}</span>
        </span>
        <button class="btn-ip" onclick="abrirModal('{{ item.ip }}', '{{ item.nome }}')">Editar</button>
        <form method="POST" action="/remover" style="margin: 0;">
          <input type="hidden" name="ip" value="{{ item.ip }}">
          <button class="btn-ip btn-delete" type="submit">Remover</button>
        </form>
      </li>
      {% endfor %}
    </ul>
  </section>
</main>
<div id="modal-editar" class="modal">
  <form method="POST" action="/editar" class="modal-content">
    <input type="hidden" id="ip_antigo" name="ip_antigo">
    <input type="text" id="novo_nome" name="novo_nome" placeholder="Novo Nome" required>
    <input type="text" id="novo_ip" name="novo_ip" placeholder="Novo IP" required>
    <button class="btn-ip" type="submit">Salvar Alterações</button>
  </form>
</div>
<script>
function abrirModal(ip, nome) {
  document.getElementById('ip_antigo').value = ip;
  document.getElementById('novo_nome').value = nome;
  document.getElementById('novo_ip').value = ip;
  document.getElementById('modal-editar').classList.add('active');
}
window.onclick = function(e) {
  if (e.target.classList.contains('modal')) {
    e.target.classList.remove('active');
  }
}
async function fetchStatus() {
  const res = await fetch('/status');
  const data = await res.json();
  document.getElementById('cpu-usage').textContent = data.cpu + '%';
  document.getElementById('internet-status').textContent = data.ping_status;
}
setInterval(fetchStatus, 2000);
fetchStatus();
</script>
</body>
</html>
'''

def validar_ip(ip):
    try:
        partes = ip.split('.')
        return len(partes) == 4 and all(0 <= int(p) <= 255 for p in partes)
    except:
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nome = request.form.get('novo-nome')
        ip = request.form.get('novo-ip')
        if nome and validar_ip(ip):
            if not any(item['ip'] == ip for item in ips_monitorados):
                ips_monitorados.append({'ip': ip, 'nome': nome})
                ips_status[ip] = False
                salvar_ips()
        return redirect('/')
    for item in ips_monitorados:
        try:
            resposta = ping(item['ip'], timeout=1)
            ips_status[item['ip']] = resposta is not None
        except:
            ips_status[item['ip']] = False
    return render_template_string(template, autorizado=True, erro=False, ips=ips_monitorados, ips_status=ips_status)

@app.route('/remover', methods=['POST'])
def remover():
    ip = request.form.get('ip')
    global ips_monitorados
    ips_monitorados = [item for item in ips_monitorados if item['ip'] != ip]
    ips_status.pop(ip, None)
    salvar_ips()
    return redirect('/')

@app.route('/editar', methods=['POST'])
def editar():
    ip_antigo = request.form.get('ip_antigo')
    novo_ip = request.form.get('novo_ip')
    novo_nome = request.form.get('novo_nome')
    global ips_monitorados
    for item in ips_monitorados:
        if item['ip'] == ip_antigo:
            item['ip'] = novo_ip
            item['nome'] = novo_nome
            break
    salvar_ips()
    return redirect('/')

@app.route('/exportar')
def exportar():
    salvar_ips()
    return send_file(DATA_FILE, as_attachment=True)

@app.route('/importar', methods=['POST'])
def importar():
    if 'arquivo' in request.files:
        file = request.files['arquivo']
        if file:
            data = json.load(file)
            if isinstance(data, list):
                global ips_monitorados
                ips_monitorados = data
                salvar_ips()
    return redirect('/')

@app.route('/status')
def status():
    net = psutil.net_io_counters()
    cpu = psutil.cpu_percent(interval=0.1)
    ping_status = 'Offline'
    try:
        response = ping('8.8.8.8', timeout=1)
        ping_status = 'Online' if response else 'Offline'
    except:
        pass
    return jsonify({
        'net_sent': round(net.bytes_sent / 1024 / 1024, 2),
        'net_recv': round(net.bytes_recv / 1024 / 1024, 2),
        'cpu': cpu,
        'ping_status': ping_status,
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
