# --- Importações de Módulos Padrão ---
import socket
import json
import sys

def send_request(host, port, request):
    """
    Função genérica para enviar uma requisição JSON para o hub e imprimir a resposta.
    Retorna True se a resposta do servidor for bem-sucedida ("status": "ok").
    """
    try:
        # Cria um socket de curta duração para cada requisição.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            sock.sendall(json.dumps(request).encode('utf-8'))
            response_data = sock.recv(4096).decode('utf-8')
            response = json.loads(response_data)
            
            # Imprime a resposta formatada para o usuário.
            print("\n< RESPOSTA DO SERVIDOR >")
            # `indent=2` formata o JSON para ser mais legível.
            # `ensure_ascii=False` permite a exibição correta de caracteres acentuados.
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
        # Pede a entrada do usuário.
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
            # Se o login for bem-sucedido, atualiza o estado para logado.
            if send_request(host, port, request):
                is_logged_in = True
        elif action == "postar":
            # Verifica se o usuário está logado antes de permitir a postagem.
            if not is_logged_in:
                print("\n[AVISO] Você precisa fazer login antes de postar uma mensagem.")
                continue
            
            message = input("  Digite sua mensagem: ")
            if message:
                request = {"action": "publish", "content": message}
                send_request(host, port, request)
        else:
            print("Comando inválido. Digite 'ajuda' para ver as opções.")

# --- Ponto de Entrada do Programa ---
if __name__ == "__main__":
    # Valida os argumentos da linha de comando.
    if len(sys.argv) != 2:
        print("Uso: python client.py <porta_do_hub>")
        print("Exemplo: python client.py 9001")
        sys.exit(1)

    # Configura o host e a porta de destino.
    target_host = 'localhost'
    target_port = int(sys.argv[1])
    
    # Inicia o loop principal do cliente.
    main_loop(target_host, target_port)
