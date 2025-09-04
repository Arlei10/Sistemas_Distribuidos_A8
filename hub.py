# -*- coding: utf-8 -*-

# --- Importações de Módulos Padrão ---
import socket
import threading
import json
import time
import sys
from datetime import datetime

# --- Configurações e Estado Global ---

# Usuários e senhas para autenticação.
AUTHENTICATED_USERS = {
    "ana": "senha321",
    "carlos": "senha654"
}

# Mural de mensagens compartilhado entre todas as threads.
MESSAGE_BOARD = []
# Lock para garantir acesso seguro ao mural de mensagens.
BOARD_LOCK = threading.Lock()

# Dicionário para rastrear sessões de usuários autenticados.
ACTIVE_SESSIONS = {}


class MessageHub:
    """Representa um único nó (servidor) na rede distribuída."""

    def __init__(self, host, port, known_hubs):
        """Construtor da classe. Configura o estado inicial do hub."""
        self.host = host
        self.port = port
        self.known_hubs = known_hubs
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.is_active = True  # Flag para simular falhas (inativar/ativar o hub).
        print(f"[*] Hub de mensagens iniciado em {host}:{port}")

    def start_server(self):
        """Inicia o servidor para escutar por conexões de entrada em um loop infinito."""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"[*] Escutando por conexões em {self.host}:{self.port}")
        while True:
            connection_socket, client_address = self.server_socket.accept()
            # Cria uma nova thread para cada cliente, permitindo múltiplas conexões simultâneas.
            handler_thread = threading.Thread(target=self.manage_connection, args=(connection_socket, client_address))
            handler_thread.start()

    def manage_connection(self, connection_socket, client_address):
        """Gerencia uma única conexão, recebendo e processando comandos."""
        print(f"[+] Conexão recebida de {client_address}")
        try:
            while True:
                payload = connection_socket.recv(4096).decode('utf-8')
                if not payload:
                    break  # Cliente desconectou.

                # Se o hub estiver inativo, rejeita a requisição.
                if not self.is_active:
                    response = {"status": "error", "content": "Hub temporariamente inativo."}
                    connection_socket.sendall(json.dumps(response).encode('utf-8'))
                    continue

                request_data = json.loads(payload)
                action = request_data.get("action")
                
                # Encaminha o comando para o método apropriado e envia a resposta.
                response = self.route_command(action, request_data, client_address)
                connection_socket.sendall(json.dumps(response).encode('utf-8'))

        except (ConnectionResetError, json.JSONDecodeError) as e:
            print(f"[!] Conexão com {client_address} perdida ou dados inválidos: {e}")
        finally:
            # Limpa a sessão e fecha a conexão.
            if client_address in ACTIVE_SESSIONS:
                del ACTIVE_SESSIONS[client_address]
            connection_socket.close()
            print(f"[-] Conexão com {client_address} fechada.")

    def route_command(self, action, request_data, client_address):
        """Chama o método correto com base na ação recebida."""
        if action == "auth":
            return self.authenticate_user(request_data, client_address)
        elif action == "publish":
            return self.publish_message(request_data, client_address)
        elif action == "fetch":
            return self.fetch_board()
        elif action == "sync":
            return self.sync_message(request_data)
        elif action == "sync_request":
            return self.process_reconciliation_request(request_data)
        else:
            return {"status": "error", "content": "Ação desconhecida."}

    def authenticate_user(self, request_data, client_address):
        """Valida as credenciais do usuário e cria uma sessão."""
        user = request_data.get("user")
        pwd = request_data.get("pass")
        if AUTHENTICATED_USERS.get(user) == pwd:
            ACTIVE_SESSIONS[client_address] = user
            print(f"[*] Usuário '{user}' autenticado de {client_address}")
            return {"status": "ok", "content": "Autenticação bem-sucedida."}
        else:
            print(f"[!] Tentativa de autenticação falhou para '{user}' de {client_address}")
            return {"status": "error", "content": "Credenciais inválidas."}
            
    def publish_message(self, request_data, client_address):
        """Adiciona uma nova mensagem ao mural e a propaga para outros hubs."""
        if client_address not in ACTIVE_SESSIONS:
            return {"status": "error", "content": "Acesso negado. Autenticação necessária."}
        
        username = ACTIVE_SESSIONS[client_address]
        message_content = request_data.get("content")
        if not message_content:
            return {"status": "error", "content": "O conteúdo da mensagem não pode ser vazio."}

        # Cria um ID único para a mensagem para evitar duplicatas na rede.
        message_uid = f"{datetime.utcnow().timestamp()}-{self.port}"
        
        new_post = {
            "uid": message_uid,
            "sender": username,
            "body": message_content,
            "created_at": datetime.utcnow().isoformat()
        }

        with BOARD_LOCK:
            MESSAGE_BOARD.append(new_post)
            print(f"[*] Nova publicação de '{username}': '{message_content}'")
        
        # Inicia a propagação da mensagem em uma nova thread (replicação assíncrona).
        threading.Thread(target=self.propagate_to_hubs, args=(new_post,)).start()
        
        return {"status": "ok", "content": "Mensagem publicada com sucesso."}

    def fetch_board(self):
        """Retorna todas as mensagens do mural."""
        with BOARD_LOCK:
            return {"status": "ok", "board": list(MESSAGE_BOARD)}

    def sync_message(self, request_data):
        """Recebe uma mensagem de outro hub e a adiciona ao mural local se não for duplicada."""
        message_data = request_data.get("message_payload")
        if not message_data or "uid" not in message_data:
            return {"status": "error", "content": "Dados de sincronização inválidos."}
        
        with BOARD_LOCK:
            is_duplicate = any(m["uid"] == message_data["uid"] for m in MESSAGE_BOARD)
            if not is_duplicate:
                MESSAGE_BOARD.append(message_data)
                print(f"[*] Mensagem sincronizada recebida: UID {message_data['uid']} de '{message_data['sender']}'")
                return {"status": "ok", "content": "Mensagem sincronizada."}
            else:
                return {"status": "ok", "content": "Mensagem já existe."}

    def propagate_to_hubs(self, message_data):
        """Envia uma nova mensagem para todos os outros hubs conhecidos."""
        print(f"[*] Propagando mensagem UID {message_data['uid']} para outros hubs...")
        payload = {
            "action": "sync",
            "message_payload": message_data
        }
        for hub_host, hub_port in self.known_hubs:
            if hub_port != self.port:
                self.send_to_hub((hub_host, hub_port), payload)

    def send_to_hub(self, hub_address, payload):
        """Estabelece uma conexão com outro hub e envia um payload."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as hub_socket:
                hub_socket.connect(hub_address)
                hub_socket.sendall(json.dumps(payload).encode('utf-8'))
                hub_socket.recv(4096)
                print(f"    -> Propagação para {hub_address} enviada.")
        except ConnectionRefusedError:
            print(f"    [!] Falha ao conectar com o hub {hub_address}. Pode estar offline.")
        except Exception as e:
            print(f"    [!] Erro ao enviar para o hub {hub_address}: {e}")
            
    def start_reconciliation(self):
        """Inicia o processo de reconciliação para obter mensagens perdidas de outros hubs."""
        if not self.is_active:
            print("[!] Hub está inativo. Fique ativo para poder reconciliar.")
            return

        print("\n[*] Iniciando processo de reconciliação...")
        with BOARD_LOCK:
            local_message_ids = {m["uid"] for m in MESSAGE_BOARD}

        payload = {
            "action": "sync_request",
            "known_uids": list(local_message_ids)
        }

        for hub_host, hub_port in self.known_hubs:
            if hub_port != self.port:
                print(f"[*] Solicitando reconciliação do hub {hub_host}:{hub_port}")
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as hub_socket:
                        hub_socket.connect((hub_host, hub_port))
                        hub_socket.sendall(json.dumps(payload).encode('utf-8'))
                        response_data = hub_socket.recv(8192).decode('utf-8')
                        response = json.loads(response_data)

                        if response.get("status") == "ok":
                            missing_posts = response.get("missing_posts", [])
                            if missing_posts:
                                with BOARD_LOCK:
                                    for post in missing_posts:
                                        if post["uid"] not in local_message_ids:
                                            MESSAGE_BOARD.append(post)
                                            print(f"    -> Mensagem reconciliada recebida: UID {post['uid']}")
                                print(f"[*] Reconciliação finalizada. {len(missing_posts)} mensagens recebidas.")
                            else:
                                print("[*] Reconciliação finalizada. Nenhuma mensagem nova.")
                            return  # Para após reconciliar com sucesso.
                        else:
                            print(f"[!] Hub {hub_host}:{hub_port} retornou um erro: {response.get('content')}")
                except Exception as e:
                    print(f"[!] Falha ao reconciliar com {hub_host}:{hub_port}: {e}")
        
        print("[!] Não foi possível reconciliar com nenhum hub disponível.")

    def process_reconciliation_request(self, request_data):
        """Responde a um pedido de reconciliação, enviando as mensagens que o outro hub não possui."""
        peer_known_uids = set(request_data.get("known_uids", []))
        
        with BOARD_LOCK:
            my_posts = list(MESSAGE_BOARD)
        
        missing_posts = [post for post in my_posts if post["uid"] not in peer_known_uids]
        
        print(f"[*] Recebido pedido de reconciliação. Enviando {len(missing_posts)} mensagens faltantes.")
        
        return {"status": "ok", "missing_posts": missing_posts}

def hub_cli(hub_instance):
    """Fornece uma CLI para administrar o hub (status, ler, desativar, etc.)."""
    time.sleep(1)
    print("\n--- Interface de Controle do Hub ---")
    print("Comandos: status, ler, desativar, ativar, reconciliar, sair")
    
    while True:
        command = input("hub> ").strip().lower()
        if command == "sair":
            print("Encerrando a interface de controle...")
            break
        elif command == "status":
            state = "Ativo" if hub_instance.is_active else "Inativo"
            print(f"Estado do Hub: {state}")
            with BOARD_LOCK:
                print(f"Mensagens no mural local: {len(MESSAGE_BOARD)}")
        elif command == "ler":
            with BOARD_LOCK:
                print("\n--- MURAL DE MENSAGENS LOCAL ---")
                if not MESSAGE_BOARD:
                    print("(Vazio)")
                else:
                    sorted_board = sorted(MESSAGE_BOARD, key=lambda x: x['created_at'])
                    for post in sorted_board:
                        print(f"  [{post['created_at']}] {post['sender']}: {post['body']}")
                print("--------------------------------\n")
        elif command == "desativar":
            if hub_instance.is_active:
                hub_instance.is_active = False
                print("\n[!] HUB DESATIVADO. Não irá processar ou propagar mensagens.\n")
            else:
                print("O hub já está desativado.")
        elif command == "ativar":
            if not hub_instance.is_active:
                hub_instance.is_active = True
                print("\n[*] HUB ATIVADO. Execute 'reconciliar' para sincronizar.\n")
            else:
                print("O hub já está ativo.")
        elif command == "reconciliar":
            hub_instance.start_reconciliation()
        else:
            print("Comando inválido.")

# --- Ponto de Entrada do Programa ---
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python hub.py <porta_local> <porta_hub1> <porta_hub2> ...")
        sys.exit(1)

    # Lê os argumentos da linha de comando para configurar o hub.
    local_port_arg = int(sys.argv[1])
    peer_ports_arg = [int(p) for p in sys.argv[2:]]
    peer_hubs_config = [('localhost', p) for p in peer_ports_arg]

    hub = MessageHub('localhost', local_port_arg, peer_hubs_config)

    # Inicia o servidor e a CLI em threads separadas para que rodem em paralelo.
    server_thread = threading.Thread(target=hub.start_server, daemon=True)
    server_thread.start()

    cli_thread = threading.Thread(target=hub_cli, args=(hub,), daemon=True)
    cli_thread.start()

    # Mantém o programa principal vivo.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSaindo do programa...")