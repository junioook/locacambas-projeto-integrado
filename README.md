# Locaçambas — Sistema de Controle de Locação de Caçambas

Projeto Integrado Interdisciplinar do CST em Análise e Desenvolvimento de Sistemas (UNOPAR, polo Parauapebas/PA).

É um protótipo funcional para controlar a locação de caçambas estacionárias de uma pequena empresa. Com ele é possível cadastrar clientes, registrar locações, consultar as caçambas em campo e registrar a retirada. A identidade visual segue a do aplicativo Locaçambas.

**Aluno:** Edson Barbosa da Silva Filho
**Tecnologias:** Python 3, Flask, SQLite

## Como executar

```bash
pip install -r requirements.txt
python app.py
```

Acesse <http://127.0.0.1:5000> e entre com:

| Usuário | Senha    |
|---------|----------|
| admin   | admin123 |

Na primeira execução, o banco `cacambas.db` é criado automaticamente, já com cinco caçambas na frota.

## Funcionalidades

| Requisito | Funcionalidade | Rota |
|-----------|----------------|------|
| RF01 | Login do atendente | `/login` |
| —    | Tela inicial com indicadores da frota e menu | `/` |
| RF02 / RF03 | Cadastrar e consultar clientes | `/clientes` |
| RF04 | Registrar locação (somente de caçamba disponível) | `/locacoes/nova` |
| RF05 | Consultar caçambas em campo | `/cacambas` |
| RF06 | Registrar retirada | `/locacoes/<id>/retirar` |

## Estrutura

```
app.py            rotas e regras de negócio
database.py       criação do banco (tabelas usuario, cliente, cacamba, locacao)
templates/        telas HTML (Jinja2)
static/           folha de estilo e logo
```
