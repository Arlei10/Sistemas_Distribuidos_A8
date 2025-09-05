import socket
import json
import sys
import threading

# Variável global para o socket, para que a thread de escuta possa acessá-lo
client_socket = None

def listen_for_server_messages(sock):
    """
    Função que roda em uma thread para escutar por mensagens do servidor.
    Isso é útil para depuração ou notificações futuras.
    """
    try:
        while True:
            # Espera por dados do servidor. O tamanho do buffer pode ser ajustado.
            response_data = sock.recv(4096)
            if not response_data:
                print("\n[INFO] Conexão com o servidor foi fechada.")
                break
            # Esta parte está desativada para não poluir o terminal,
            # mas pode ser usada para depurar respostas inesperadas.
            # print(f"\n< MENSAGEM DO SERVIDOR (não solicitada) >\n{response_data.decode('utf-8')}\ncliente> ", end="")
    except (ConnectionResetError, ConnectionAbortedError, OSError):
        print("\n[INFO] A conexão com o servidor foi perdida.")
    except Exception as e:
        # Captura outras exceções que possam ocorrer
        print(f"\n[ERRO] Erro na thread de escuta: {e}")

def send_request(sock, request):
    """Envia uma requisição ao servidor e aguarda uma única resposta."""
    try:
        # Envia o payload da requisição, codificado em JSON e UTF-8
        sock.sendall(json.dumps(request).encode('utf-8'))
        # Aguarda e decodifica a resposta
        response_data = sock.recv(4096).decode('utf-8')
        response = json.loads(response_data)
        
        # Imprime a resposta formatada para o usuário
        print("\n< RESPOSTA DO SERVIDOR >")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        print("------------------------")
        
        # Retorna True se a operação foi bem-sucedida
        return response.get("status") == "ok"

    except (ConnectionResetError, ConnectionAbortedError):
        print("\n[ERRO] A conexão com o servidor foi perdida. Tente reconectar.")
        return False
    except json.JSONDecodeError:
        print("\n[ERRO] Resposta inválida do servidor. Não era um JSON válido.")
        return False
    except Exception as e:
        print(f"\n[ERRO] Falha ao comunicar com o hub: {e}")
        return False

def main_loop(host, port):
    """ Loop principal da interface do cliente, que gerencia a conexão e os comandos. """
    global client_socket
    is_logged_in = False

    try:
        # Cria e conecta o socket UMA VEZ no início
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        print(f"Cliente conectado ao Hub em {host}:{port}. Digite 'ajuda' para ver os comandos.")
        
        # Inicia a thread para escutar mensagens em segundo plano
        # threading.Thread(target=listen_for_server_messages, args=(client_socket,), daemon=True).start()

    except Exception as e:
        print(f"[ERRO] Não foi possível conectar ao hub em {host}:{port}. Erro: {e}")
        return # Encerra se não conseguir conectar

    # Loop de comandos do usuário
    while True:
        try:
            action = input("cliente> ").strip().lower()

            if action == "sair":
                break
            elif action == "ajuda":
                print("\nComandos disponíveis:")
                print("  login   - Autenticar no sistema.")
                print("  postar  - Publicar uma nova mensagem (requer login).")
                print("  ler     - Ler todas as mensagens do mural.")
                print("  sair    - Fechar o cliente.")
            elif action == "ler":
                send_request(client_socket, {"action": "fetch"})
            elif action == "login":
                user = input("  Usuário: ")
                password = input("  Senha: ")
                request = {"action": "auth", "user": user, "pass": password}
                # Atualiza o estado de login se a requisição for bem-sucedida
                if send_request(client_socket, request):
                    is_logged_in = True
            elif action == "postar":
                if not is_logged_in:
                    print("\n[AVISO] Você precisa fazer login antes de postar uma mensagem.")
                    continue
                
                # Loop para permitir múltiplas postagens
                print("--- Modo de Postagem (digite 'SAIR' para voltar ao menu) ---")
                while True:
                    message = input("  postar> ")
                    if message.upper() == 'SAIR':
                        break
                    if message:
                        request = {"action": "publish", "content": message}
                        send_request(client_socket, request)
            else:
                print("Comando inválido. Digite 'ajuda' para ver as opções.")
        
        except KeyboardInterrupt:
            # Permite sair com Ctrl+C
            break

    # Fecha o socket ao sair do loop
    client_socket.close()
    print("\nConexão encerrada.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python client.py <porta_do_hub>")
        print("Exemplo: python client.py 9001")
        sys.exit(1)

    target_host = 'localhost'
    target_port = int(sys.argv[1])
    
    main_loop(target_host, target_port)

