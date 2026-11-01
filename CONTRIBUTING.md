# Como contribuir com acompanhamento_de_np

Obrigado pela ajuda.

## Como contribuir

1. Faca um fork do repositorio e clone o seu fork.
2. Crie uma branch a partir de `develop` (`feat/nome-curto`, `fix/nome-curto`, `docs/nome-curto`).
3. Faca commits pequenos com mensagens no padrao conventional commits.
4. Abra um pull request para `develop`, nunca para `main`, e preencha o template.
5. A integracao continua precisa passar e o mantenedor precisa aprovar
   (`.github/CODEOWNERS`). As revisoes podem ter apoio de um revisor de IA; a
   aprovacao final e sempre humana.
6. Os pull requests entram em `develop` com squash merge. O mantenedor publica
   `develop` em `main` por um pull request de release.

As branches `main` e `develop` sao protegidas: sem push direto, sem force push e
sem exclusao. Pull requests vindos de forks so rodam a CI depois que o mantenedor
aprova a execucao.

Seguranca: veja `SECURITY.md`. Conduta: veja `CODE_OF_CONDUCT.md`.
