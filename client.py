import socket
import json
import sys

def send_request(host, port, request):

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            sock.sendall(json.dumps(request).encode('utf-8'))
            response_data = sock.recv(4096).decode('utf-8')
            response = json.loads(response_data)
            
            print("\n< RESPOSTA DO SERVIDOR >")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            print("------------------------")
            return response.get("status") == "ok"

    except Exception as e:
        print(f"\n[ERRO] Não foi possível conectar ao hub em {host}:{port}. Erro: {e}")
        return False

def main_loop(host, port):
    """ Loop principal da interface do cliente. """
    is_logged_in = False
    print(f"Cliente conectado ao Hub em {host}:{port}. Digite 'ajuda' para ver os comandos.")

    while True:
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
            send_request(host, port, {"action": "fetch"})
        elif action == "login":
            user = input("  Usuário: ")
            password = input("  Senha: ")
            request = {"action": "auth", "user": user, "pass": password}
            if send_request(host, port, request):
                is_logged_in = True
        elif action == "postar":
            if not is_logged_in:
                print("\n[AVISO] Você precisa fazer login antes de postar uma mensagem.")
                continue
            
            message = input("  Digite sua mensagem: ")
            if message:
                request = {"action": "publish", "content": message}
                send_request(host, port, request)
        else:
            print("Comando inválido. Digite 'ajuda' para ver as opções.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python client.py <porta_do_hub>")
        print("Exemplo: python client.py 9001")
        sys.exit(1)

    target_host = 'localhost'
    target_port = int(sys.argv[1])
    
    main_loop(target_host, target_port)
