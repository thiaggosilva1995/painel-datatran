# Enviar o projeto ao GitHub

O arquivo `painel-datatran-github.zip` contém o código, estilos, bibliotecas de visualização, migrações, testes, documentação e a base original `data/datatran2026.csv`.

## Pelo navegador

1. Extraia o ZIP no computador.
2. Crie um repositório no GitHub, escolhendo a visibilidade desejada.
3. Use **Add file → Upload files** e envie o conteúdo da pasta `painel-datatran`, preservando os diretórios. Inclua `.gitignore` e `.env.example`.
4. Confirme os arquivos em **Commit changes**.

Para disponibilizar o código navegável no repositório, envie os arquivos extraídos. Você também pode anexar o ZIP a uma Release como download adicional.

## Pelo terminal

Na pasta extraída `painel-datatran`, execute os comandos abaixo. Substitua `SEU_USUARIO/SEU_REPOSITORIO` pelo endereço do seu repositório vazio.

```bash
git init
git add .
git commit -m "Adiciona painel DATATRAN com identidade PMPB"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

A autenticação é feita pela sua conta GitHub. Não coloque tokens em arquivos do projeto.

## Executar após baixar

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py processar_datatran
python manage.py runserver
```

Abra http://127.0.0.1:8000. Confira os testes com `python manage.py test dashboard`.

O código Django precisa de um servidor Python para executar; publicar os arquivos no GitHub não inicia a aplicação.

## Conteúdo excluído

- `venv`, caches Python e arquivos internos do editor/assistente;
- banco SQLite com sessões e histórico local;
- credenciais, arquivos `.env` locais e configurações AWS;
- uploads, backups e snapshots processados (gerados novamente pelos comandos acima).

A base CSV original está incluída. A antiga chave de desenvolvimento foi substituída por configuração via `DJANGO_SECRET_KEY`, com valor padrão apenas para uso local.
