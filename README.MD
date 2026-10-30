# Projeto IA Local

Primeira versão funcional de uma aplicação web de inteligência artificial, desenvolvida com Python e Flask, com autenticação de usuários e integração com um modelo de linguagem executado localmente.

## Funcionalidades

- Cadastro e autenticação de usuários.
- Gerenciamento de sessão.
- Interface de chat com IA.
- Comunicação entre o backend Flask e a API local do modelo.
- Organização do código em módulos.
- Controle de requisições simultâneas ao modelo.

## Tecnologias

- Python
- Flask
- HTML, CSS e JavaScript
- bcrypt
- API compatível com o formato OpenAI Chat Completions
- Modelo de linguagem local

## Requisitos

- Python compatível com as dependências do projeto.
- Modelo de linguagem local configurado e em execução.
- Dependências listadas em `requirements.txt`.

## Instalação

1. Clone este repositório.
2. Crie e ative um ambiente virtual Python.
3. Instale as dependências com `python -m pip install -r requeriments.txt`.
4. Configure as variáveis de ambiente necessárias.
5. Inicie o serviço local do modelo de IA.
6. Execute a aplicação Flask.

## Segurança

Dados de usuários, credenciais, chaves privadas, arquivos de configuração locais e pesos dos modelos não devem ser versionados neste repositório.

## Status

Primeira versão funcional. O projeto continuará recebendo melhorias de arquitetura, segurança e manutenção.

## Licença

A definir.
