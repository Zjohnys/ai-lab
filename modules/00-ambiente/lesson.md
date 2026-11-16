# Módulo 0 - Ambiente profissional com IA

Objetivo: sair deste módulo com um ambiente em que você planeja, edita, testa, revisa e publica do mesmo jeito que um time profissional, com a IA dentro do fluxo e um modelo local rodando.

## 1. O fluxo de trabalho

Todo lote de trabalho neste projeto segue a mesma sequência:

1. **Planejar.** Escreva o que vai mudar antes de mudar. Com IA, peça o plano primeiro e só depois o código.
2. **Lote pequeno.** No máximo 3 itens. Um diff de 50 linhas você revisa de verdade; um de 800 você só rola a tela.
3. **Testar.** Rode os testes a cada lote, não no fim do dia.
4. **Revisar o diff linha a linha.** Código gerado por IA é código de um colega que você não conhece: leia tudo.
5. **Commit pequeno** com mensagem clara, em uma branch, e pull request para a `main`.

Ao revisar código gerado por IA, procure nesta ordem:

| Pergunta | Exemplo do que procurar |
| --- | --- |
| Faz o que foi pedido, e só isso? | Arquivos alterados que você não pediu, dependências novas |
| É seguro? | Segredo no código, entrada do usuário usada sem validação, comando de shell montado com texto |
| E os casos extremos? | Lista vazia, valor nulo, erro de rede, resposta do modelo em formato errado |
| Os testes testam algo? | Teste que nunca falha, teste que só repete a implementação |
| Eu sei explicar cada linha? | Se não sabe, pergunte antes de aceitar |

## 2. VS Code

### Atalhos que pagam o investimento

| Atalho | Nome | Quando usar |
| --- | --- | --- |
| `Ctrl+Shift+P` | Command Palette | Qualquer comando do editor pelo nome; se esqueceu um atalho, comece aqui |
| `Ctrl+P` | Quick Open | Abrir arquivo pelo nome, sem usar a árvore de pastas |
| `Ctrl+Shift+F` | Search in project | Achar todos os usos de um texto no projeto |
| `Ctrl+Shift+O` | Go to Symbol | Pular para uma função ou classe dentro do arquivo |
| `Ctrl+G` | Go to Line | Ir para a linha citada em um erro |
| `F12` / `Shift+F12` | Go to Definition / References | Ver onde algo é definido e quem usa |
| `F2` | Rename Symbol | Renomear em todos os arquivos, com segurança |
| `Ctrl+.` | Quick Fix | Aplicar a correção sugerida (import faltando, por exemplo) |
| `Ctrl+D` | Add next occurrence | Multi-cursor: selecionar a próxima ocorrência igual |
| `Alt+Click` | Add cursor | Multi-cursor em posições arbitrárias |
| `Ctrl+Alt+Up/Down` | Add cursor above/below | Editar várias linhas alinhadas |
| `Alt+Up/Down` | Move line | Mover a linha sem recortar e colar |
| `Shift+Alt+Up/Down` | Copy line | Duplicar a linha |
| `Ctrl+/` | Toggle comment | Comentar ou descomentar a seleção |
| ``Ctrl+` `` | Integrated terminal | Abrir o terminal sem sair do editor |
| `Ctrl+Shift+G` | Source Control | Ver o diff antes de commitar |
| `Ctrl+Shift+B` | Run Build Task | Neste projeto: sobe backend e frontend juntos |
| `F5` / `F9` / `F10` / `F11` | Debug | Iniciar, breakpoint, passar por cima, entrar na função |
| `Ctrl+,` | Settings | Configurações; `Ctrl+K Ctrl+S` abre os atalhos |

### Arquivos em `.vscode/`

- **`settings.json`**: configurações do projeto, versionadas. Valem para qualquer pessoa que abrir o repositório e têm prioridade sobre as suas configurações pessoais. Aqui: formatar ao salvar, Ruff para Python, Prettier para TypeScript, pytest apontando para `backend`.
- **`extensions.json`**: extensões recomendadas. O VS Code oferece instalar ao abrir a pasta.
- **`tasks.json`**: comandos nomeados. `Ctrl+Shift+P`, "Tasks: Run Task". Evita decorar comandos e garante que todos rodam igual.
- **`launch.json`**: configurações do debugger. `F5` sobe o FastAPI com breakpoints.

### Debugger em vez de `print`

1. Abra `backend/app/main.py` e pressione `F9` na linha do `return` da função `health`.
2. `F5` e escolha "Backend: FastAPI (debug)".
3. Abra `backend/requests.http` e clique em "Send Request" no health.
4. A execução para na linha. Inspecione variáveis no painel, `F10` avança, `F5` continua.

Use o debugger quando não sabe o valor de algo no meio do caminho. `print` serve para uma checagem rápida; para entender um fluxo, o debugger é mais rápido.

### Extensões deste projeto

| Extensão | Para que serve |
| --- | --- |
| Python + debugpy | Interpretador, testes e debugger |
| Ruff | Lint e formatação de Python |
| Prettier | Formatação de TypeScript, JSON e CSS |
| Tailwind CSS IntelliSense | Autocompletar classes |
| GitLens | Quem mudou cada linha e por quê (blame) |
| Error Lens | Mostra o erro na própria linha, sem passar o mouse |
| REST Client | Chamar a API a partir de um arquivo `.http` versionado |
| EditorConfig | Aplica o `.editorconfig` |
| GitHub Actions | Ver o CI sem sair do editor |

O template atual do Vite usa `oxlint` no lugar do ESLint, então o lint do frontend roda por `npm run lint`.

## 3. IA no editor

### Três modos, três usos

| Modo | O que é | Quando usar |
| --- | --- | --- |
| Chat | Perguntar sem alterar arquivos | Entender código, comparar abordagens, pedir um plano |
| Edição pontual | Alterar um trecho selecionado | Mudança pequena e local, que você sabe descrever em uma frase |
| Agente | A IA lê arquivos, roda comandos e edita em vários lugares | Tarefa com vários passos: criar um endpoint com teste, refatorar um módulo |

Quanto mais autonomia, maior o diff e maior a sua responsabilidade na revisão. Comece pelo modo mais restrito que resolve.

### Dar contexto

A qualidade da resposta depende mais do contexto do que do modelo:

- **Aponte arquivos e trechos.** Mencione o arquivo com `@` ou selecione o código antes de perguntar.
- **Cole o erro inteiro**, com o stack trace, e diga o que você esperava.
- **Diga o que não fazer.** "Não adicione dependências" economiza uma rodada.
- **Peça o plano antes do código** em tarefas com mais de um arquivo.

### `CLAUDE.md`

Arquivo na raiz que o Claude Code lê em toda sessão. É onde ficam as regras que você não quer repetir: stack, comandos, convenções de commit, o que nunca fazer. Trate como código: versionado, revisado e curto. Regra que não muda o comportamento da IA deve sair.

### Alternativas locais no editor

Extensões como o Continue conectam o VS Code a um modelo no Ollama, para chat e autocompletar sem nuvem.

- **Fazem sentido** quando o código não pode sair da máquina, quando você está sem internet, ou para autocompletar com um modelo pequeno e rápido.
- **Limite neste hardware:** com 8 GB de VRAM cabe um modelo de 7 a 8B por vez. Ele explica e completa trechos bem, mas erra mais em tarefas de agente com vários arquivos e chamadas de ferramenta. O Módulo 6 mede esse limite em vez de só afirmar.

## 4. Terminal e Git

### PowerShell no dia a dia

| Comando | Para que serve |
| --- | --- |
| `cd pasta`, `cd ..` | Navegar |
| `ls` (`Get-ChildItem`) | Listar arquivos |
| `cat arquivo` (`Get-Content`) | Ver conteúdo |
| `cmd1; cmd2` | Encadear comandos (no PowerShell 5.1 não existe `&&`) |
| `$env:NOME` | Ler uma variável de ambiente |
| `Get-Command nome` | Descobrir se um programa está no PATH e onde |
| `code .` | Abrir a pasta atual no VS Code |

### Git: o ciclo que você vai repetir

```powershell
git switch -c feat/minha-mudanca     # branch nova a partir da atual
git status                           # o que mudou
git diff                             # o que mudou, linha a linha
git add caminho/do/arquivo           # escolher o que entra no commit
git commit -m "feat: add version endpoint"
git push -u origin feat/minha-mudanca
gh pr create --fill                  # pull request com o texto dos commits
gh pr merge --merge --delete-branch  # depois de revisar
git switch main; git pull            # atualizar a main local
```

- **Conventional Commits:** `feat:` funcionalidade, `fix:` correção, `docs:` documentação, `test:` testes, `chore:` manutenção.
- **`.gitignore`:** o que nunca entra no repositório (`.env`, `node_modules`, `.venv`, bancos, modelos).
- **`.env` e `.env.example`:** o primeiro tem os valores reais e é ignorado; o segundo documenta as variáveis e é versionado.
- **Commit pequeno:** uma ideia por commit. Se a mensagem precisa de "e", provavelmente são dois commits.

## 5. Ollama

```powershell
ollama pull qwen3:8b             # baixar um modelo
ollama list                      # modelos instalados
ollama run qwen3:8b --verbose    # conversar e ver tokens/s ao final
ollama ps                        # modelos carregados e divisão GPU/CPU
ollama stop qwen3:8b             # liberar a memória
```

O que observar:

- **`PROCESSOR` no `ollama ps`:** `100% GPU` é o objetivo. Qualquer parte em CPU indica que o modelo ou o contexto não coube na VRAM.
- **Primeira resposta lenta:** o modelo é carregado na primeira chamada e fica na memória por 5 minutos. Meça a execução quente separada da fria.
- **`num_ctx`:** tamanho da janela de contexto. Quando o prompt passa do limite, o Ollama corta o início em silêncio. Sempre defina explicitamente.
- **Local dos modelos:** o app do Ollama usa a pasta definida nas configurações dele; o servidor iniciado por `ollama serve` usa a variável `OLLAMA_MODELS`. Mantenha as duas iguais.

O Ollama expõe uma API HTTP em `http://localhost:11434`. O arquivo `backend/requests.http` tem exemplos prontos.
