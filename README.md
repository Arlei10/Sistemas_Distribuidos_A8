#  Projeto: Mural de Mensagens Distribuído

Este projeto demonstra um sistema distribuído simples para publicação e leitura de mensagens. O foco principal é explorar os conceitos de **replicação de dados**, **consistência eventual** e **recuperação de falhas** em um ambiente com múltiplos nós (hubs).

---

##  Visão Geral da Arquitetura

- **Modelo Peer-to-Peer (P2P):**  
  O sistema não possui um servidor central. Cada instância do programa (`hub.py`) atua como um nó autônomo (chamado de Hub) que se comunica diretamente com os outros.

- **Replicação de Dados:**  
  Cada hub mantém uma cópia local completa do mural de mensagens. Quando uma nova mensagem é publicada em um hub, ele a replica para todos os outros hubs conhecidos.

- **Comunicação via Sockets TCP:**  
  A troca de mensagens entre os hubs é feita utilizando o protocolo TCP, garantindo uma comunicação confiável.

- **Consistência Eventual:**  
  A replicação é assíncrona. Pode haver um pequeno atraso até que uma nova mensagem se propague por toda a rede. No entanto, se não houver novas publicações, todos os hubs eventualmente terão o mesmo conjunto de mensagens.

- **Tolerância a Falhas:**  
  O sistema é projetado para lidar com a queda temporária de um hub. Após a reconexão, o hub pode iniciar um processo de reconciliação para sincronizar as mensagens que perdeu.

---

##  Estrutura dos Arquivos

| Arquivo      | Descrição                                                                 |
|--------------|---------------------------------------------------------------------------|
| `hub.py`     | Código principal do servidor/nó. Cada execução representa um hub no sistema. |
| `client.py`  | Cliente de terminal para interagir com os hubs (login, postagem, leitura). |
| `README.md`  | Este arquivo, com instruções de execução e documentação.                   |



##  Guia de Execução e Teste

###  Passo 1: Iniciar os Hubs

Abra **três terminais** na pasta do projeto, um para cada hub:

- **Terminal 1 (Hub A):**
  ```bash
  python hub.py 9001 9002 9003

- **Terminal 2 (Hub B):**
  ```bash
  python hub.py 9002 9001 9003

- **Terminal 3 (Hub C):**
  ```bash
  python hub.py 9003 9001 9002

- Ao final, você terá três hubs rodando e se comunicando. Cada terminal terá um prompt hub> para comandos administrativos.

###  Passo 2: Interagir com o Sistema usando o Cliente
Para publicar e ler mensagens, usaremos o client.py.

* Abra um quarto terminal.

Execute o cliente, apontando para a porta de qualquer hub ativo (por exemplo, o Hub A na porta 9001):

 ```bash
 - python hub.py 9002 9001 9003
 ```

Você verá um prompt cliente>. Use os seguintes comandos:

- ajuda: Mostra a lista de comandos disponíveis.

- ler: Busca e exibe todas as mensagens do mural. Não precisa de login.

- login: Inicia o processo de autenticação. O programa pedirá um usuário e senha:

" Usuários de teste: ana (senha: senha321), carlos (senha: senha654). " 

- Após o login bem-sucedido, você entrará em um modo de postagem (postar>). Digite suas mensagens e pressione Enter para publicar. Para sair, digite SAIR.

###  Passo 3: Simular uma Falha e Recuperação

Este é o teste principal para observar a consistência eventual.

**1. Desative um Hub: No Terminal 3 (Hub C), digite o comando administrativo:**
  ```bash
hub> desativar
  ```
O Hub C agora irá ignorar todas as novas mensagens.

**2. Publique uma Mensagem: No Terminal 4 (cliente), conecte-se ao Hub A (python client.py 9001), faça login como ana e poste uma mensagem como "Esta mensagem foi enviada durante a falha".**  

**3. Verifique o Estado:**

Nos terminais dos Hubs A e B, use o comando ler. A nova mensagem aparecerá.

No terminal do Hub C, use o comando ler. A nova mensagem não aparecerá.

**4. Ative o Hub com Falha: No Terminal 3 (Hub C), digite:**
```bash
hub> ativar
```
**5. Inicie a Reconciliação: Ainda no Terminal 3, digite:**
  ```bash
hub> reconciliar
  ```
Você verá logs indicando que o Hub C está buscando e recebendo as mensagens que perdeu dos outros hubs.

**6. Verifique a Consistência Final: Digite ler no Terminal 3 mais uma vez. A mensagem "Esta mensagem foi enviada durante a falha" agora deve aparecer. O sistema está novamente consistente!**
