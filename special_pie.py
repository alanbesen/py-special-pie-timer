import asyncio
from bleak import BleakClient

address = "54:14:A7:77:02:A2"  # Substitua pelo endereço do seu dispositivo
characteristic_uuid = "0000fff1-0000-1000-8000-00805f9b34fb" 

previous_time_seconds = None
previous_time_ms = None

async def connect_and_subscribe(address):
    async with BleakClient(address) as client:
        # Verifica se o dispositivo está conectado
        is_connected = await client.is_connected()
        print(f"Conectado: {is_connected}")
        
        if is_connected:
            # Habilita notificações para a característica
            await client.start_notify(characteristic_uuid, notification_handler)
            print(f"Inscrição para notificações ativada na característica: {characteristic_uuid}")
            
            
            while True:
                await asyncio.sleep(1)  # Espera um pouco para receber notificações

def parse_raw_data(data):
    # Converte bytearray para representação hexadecimal
    hex_data = ' '.join(format(x, '02x') for x in data)
    return hex_data

def interpret_hex_data(hex_data):
    # Dividir os dados hexadecimais em partes
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

async def notification_handler(sender, data):
    global previous_time_seconds, previous_time_ms
    
    # Converte bytearray para representação hexadecimal
    hex_data = parse_raw_data(data)
    
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
    
    if int_values[2] == 54:
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
            delta_time_formatted = f"{delta_seconds}.{delta_ms:02}"
            
            print(f"SHOT: {split_value} - TIME: {current_time_formatted} | SPLIT: {delta_time_formatted}")
            last_time = current_time_formatted
        else:
            # Primeira vez recebendo um valor válido, apenas armazena o tempo atual
            previous_time_seconds = current_time_seconds
            previous_time_ms = current_time_ms
    elif int_values[2] == 52: 
        print('start')
    elif int_values[2] == 24: 
        print('stop')
    else:
        pass

# Loop principal para execução do código assíncrono
loop = asyncio.get_event_loop()
loop.run_until_complete(connect_and_subscribe(address))
