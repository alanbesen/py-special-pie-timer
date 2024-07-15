from flask import Flask, render_template, request, jsonify
import asyncio
from bleak import BleakScanner, BleakClient
import threading
import json

app = Flask(__name__)

# Variável global para armazenar o loop de eventos assíncrono
loop = None

# Variável global para armazenar o endereço do dispositivo selecionado
selected_device_address = None

# Variáveis globais para armazenar o tempo anterior
previous_time_seconds = None
previous_time_ms = None

# Variável global para controlar o estado de notificações (start/stop)
notifications_active = False

# Lista global para armazenar resultados
results = []

# Função para carregar o último dispositivo selecionado
def load_last_device():
    try:
        with open('last_device.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# Função para salvar o dispositivo selecionado em um arquivo JSON
def save_last_device(device_address):
    data = {'device_address': device_address}
    with open('last_device.json', 'w') as f:
        json.dump(data, f)

@app.route('/')
def index():
    global selected_device_address
    # Carregar o último dispositivo selecionado
    last_device = load_last_device()
    if last_device:
        selected_device_address = last_device.get('device_address')
    
    # Se houver um último dispositivo selecionado, iniciar automaticamente as notificações
    if selected_device_address:
        if loop is None or loop.is_closed():
            start_asyncio_loop()
        threading.Thread(target=asyncio.run, args=(connect_and_subscribe(selected_device_address),)).start()
        # Marcar notificações como ativas
        notifications_active = True
    
    devices = discover_devices_ble()
    return render_template('index.html', devices=devices)

@app.route('/start_notifications', methods=['POST'])
def start_notifications():
    global selected_device_address, notifications_active, results
    selected_device_address = request.form['device']
    
    if loop is None or loop.is_closed():
        start_asyncio_loop()

    threading.Thread(target=asyncio.run, args=(connect_and_subscribe(selected_device_address),)).start()
    
    # Marcar notificações como ativas
    notifications_active = True
    results = []  # Limpar os resultados ao iniciar

    # Salvar o dispositivo selecionado
    save_last_device(selected_device_address)

    return 'Started notifications for device: ' + selected_device_address

@app.route('/stop_notifications', methods=['POST'])
def stop_notifications():
    global notifications_active, results
    notifications_active = False
    results = []  # Limpar os resultados ao parar
    return 'Stopped notifications for device: ' + selected_device_address

@app.route('/update_results', methods=['GET'])
def update_results():
    global results
    return jsonify(results)

async def connect_and_subscribe(address):
    global loop
    characteristic_uuid = "0000fff1-0000-1000-8000-00805f9b34fb"

    async with BleakClient(address, loop=loop) as client:
        # Verifica se o dispositivo está conectado
        is_connected = await client.is_connected()
        print(f"Conectado: {is_connected}")

        if is_connected:
            # Habilita notificações para a característica
            await client.start_notify(characteristic_uuid, notification_handler)
            print(f"Inscrição para notificações ativada na característica: {characteristic_uuid}")

            while notifications_active:
                await asyncio.sleep(1)  # Espera um pouco para receber notificações

async def notification_handler(sender, data):
    global loop, selected_device_address, previous_time_seconds, previous_time_ms, results

    if selected_device_address and notifications_active:
        # Converte bytearray para representação hexadecimal
        hex_data = ' '.join(format(x, '02x') for x in data)

        # Interpretar os dados hexadecimais para uma string significativa
        interpreted_string = interpret_hex_data(hex_data)

        # Exibir ambos os formatos (int e string) para comparação
        # print(f"Recebido dados da notificação (String): {interpreted_string}")

        # Exibir como inteiros
        int_values = []
        parts = hex_data.split(' ')
        for i in range(len(parts)):
            try:
                int_value = int(parts[i], 16)
                int_values.append(int_value)
            except ValueError:
                pass  # Não é um valor numérico válido

        # print(f"Recebido dados da notificação (Int): {int_values}")

        if int_values and int_values[2] == 54:
            last_time = ''
            current_time_seconds = int_values[4]
            current_time_ms = int_values[5]

            if previous_time_seconds is not None and previous_time_ms is not None:
                # Calcular a diferença de tempo
                delta_seconds = current_time_seconds - previous_time_seconds
                delta_ms = current_time_ms - previous_time_ms

                # Atualizar o tempo anterior para o atual
                previous_time_seconds = current_time_seconds
                previous_time_ms = current_time_ms

                # Corrigir a diferença de tempo para garantir que seja positiva
                if delta_ms < 0:
                    delta_seconds -= 1
                    delta_ms += 100  # 100 milissegundos em um segundo

                # Formatar a saída
                split_value = int_values[6]
                current_time_formatted = f"{current_time_seconds}.{current_time_ms:02}"
                delta_time_formatted = f"{delta_seconds}.{abs(delta_ms):02}"

                print(f"SHOT: {split_value} - TIME: {current_time_formatted} | SPLIT: {delta_time_formatted}")
                last_time = current_time_formatted
                results.append({
                    'shot': split_value,
                    'time': current_time_formatted,
                    'delta_time': delta_time_formatted
                })
                # Enviar para a página web via WebSocket
                await send_data_to_web(current_time_formatted, delta_time_formatted)
            else:
                # Primeira vez recebendo um valor válido, apenas armazena o tempo atual
                previous_time_seconds = current_time_seconds
                previous_time_ms = current_time_ms
        elif int_values and int_values[2] == 52:
            print('start')
            results = []  # Limpar os resultados quando receber o start
        elif int_values and int_values[2] == 24:
            print('stop')

        else:
            pass

def start_asyncio_loop():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def send_data_to_web(current_time, delta_time):
    # Implemente o envio dos dados para a página web aqui
    # Exemplo: usar Flask-SocketIO para enviar dados via WebSocket
    pass

def discover_devices_ble():
    # Implemente a descoberta de dispositivos BLE aqui
    # Exemplo fictício usando BleakScanner
    discovered_devices = []

    async def scan():
        devices = await BleakScanner.discover()
        for device in devices:
            discovered_devices.append(device)

    asyncio.run(scan())

    return discovered_devices

def interpret_hex_data(hex_data):
    # Implemente a interpretação dos dados hexadecimais aqui
    parts = hex_data.split(' ')

    interpreted_string = ""
    for i in range(len(parts)):
        if parts[i] == 'f8':
            interpreted_string += "Inicio de transmissão | "
        elif parts[i] == 'f9':
            interpreted_string += "Fim de transmissão | "
        elif parts[i] == '36':
            # Interpretar os dados específicos após '36'
            if i + 4 < len(parts):
                data_value = parts[i + 1:i + 4]  # Pegar os próximos três bytes
                data_value_str = ' '.join(data_value)
                interpreted_string += f"Dado específico: {data_value_str} | "
                # Converter para int se for um valor numérico conhecido
                try:
                    int_value = int(''.join(data_value), 16)
                    interpreted_string += f"Dado convertido para int: {int_value} | "
                except ValueError:
                    pass  # Não é um valor numérico válido
            else:
                interpreted_string += "Dados incompletos após '36' | "
        else:
            interpreted_string += f"Desconhecido: {parts[i]} | "
            # Tentar converter desconhecido para int
            try:
                int_value = int(parts[i], 16)
                interpreted_string += f"Desconhecido convertido para int: {int_value} | "
            except ValueError:
                pass

    return interpreted_string

if __name__ == '__main__':
    app.run(debug=True)
