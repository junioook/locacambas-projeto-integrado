# Sistema de Controle de Locação de Caçambas

Projeto Integrado Interdisciplinar — protótipo funcional para controlar a locação de caçambas estacionárias de uma pequena empresa: cadastro de clientes, registro de locações, consulta das caçambas em campo e registro de retirada.

**Tecnologias:** Python 3, Flask, SQLite.

## Como executar

```bash
pip install -r requirements.txt
python app.py
```

Acesse <http://127.0.0.1:5000> e entre com:

| Usuário | Senha    |
|---------|----------|
| admin   | admin123 |

O banco `cacambas.db` é criado automaticamente na primeira execução, já com cinco caçambas na frota.

## Funcionalidades

| Requisito | Funcionalidade | Rota |
|-----------|----------------|------|
| RF01 | Login do atendente | `/login` |
| RF02 / RF03 | Cadastrar e consultar clientes | `/clientes` |
| RF04 | Registrar locação (só caçamba disponível) | `/locacoes/nova` |
| RF05 | Consultar caçambas em campo | `/cacambas` |
| RF06 | Registrar retirada | `/locacoes/<id>/retirar` |

## Estrutura

```
app.py            rotas e regras de negócio
database.py       criação do banco (tabelas usuario, cliente, cacamba, locacao)
templates/        telas HTML (Jinja2)
static/           folha de estilo
```
