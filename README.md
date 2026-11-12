# Game Shelf

Every game I've beaten, ranked, with hours played.
**Live:** https://m-imaaz-tarapathi.github.io/game-shelf/

A static site on GitHub Pages with no backend:

- **Data** lives in [`data/games.json`](data/games.json). The page edits it in place through the GitHub API, using a fine-grained token that only stays on my own devices. Visitors get a read-only view.
- **Covers** come from [IGDB](https://www.igdb.com). When a game is added, the [Fetch covers](.github/workflows/covers.yml) action finds its official cover and commits it to `covers/`.
- **Steam playtime** is pulled daily by the [Steam sync](.github/workflows/steam.yml) action into `data/steam.json`. On the site I review the differences and choose which to apply.
- **Now playing** sits above the shelf: a game marked `"playing": true` shows its live Steam hours there, and "Finished it" moves it onto the shelf with its final hours.

Built with plain HTML, CSS and JavaScript (canvas for the nebula and spider lily), plus Python and GitHub Actions for the data pipeline.
