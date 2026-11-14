# Installation options

## Recommended: GitHub CLI

Use the same command in macOS/Linux Terminal and Windows PowerShell:

```sh
gh skill install OptimistOtaku/Codexter codex-cleanup --agent codex --scope user
```

Requirements: a recent GitHub CLI that supports `gh skill install`, plus normal GitHub authentication if requested (`gh auth login`). Tested locally with GitHub CLI 2.102.0. The skill commands are currently a preview; older GitHub CLI versions may need an update. Installation does not require Node.js, a local repository checkout or administrator privileges. The installed helper separately needs Python 3.10+ and Git.

The skill name, `--agent codex` and `--scope user` remove selection prompts and make this skill available across projects. No `--force` is used. Review an existing installation before overwriting local changes.

GitHub CLI records source metadata in the installed `SKILL.md`; keep that local metadata out of the source repository. It chooses the latest tagged release when available, otherwise the default branch. To inspect or pin a version:

```sh
gh skill preview OptimistOtaku/Codexter codex-cleanup
gh skill install OptimistOtaku/Codexter codex-cleanup --agent codex --scope user --pin <tag-or-commit>
```

For one project only, run inside that project and replace `--scope user` with `--scope project`. To inspect and update an installation:

```sh
gh skill list --agent codex
gh skill update codex-cleanup --dry-run
gh skill update codex-cleanup
```

An older manual installation may lack source metadata. In that case, inspect it and let the interactive updater request the source repository. Do not install a second copy in another discovery directory as a workaround. Pinned installations are excluded from normal updates until explicitly unpinned.

Sources: [install](https://cli.github.com/manual/gh_skill_install), [preview status](https://cli.github.com/manual/gh_skill), [updates](https://cli.github.com/manual/gh_skill_update).

## Inside Codex: no terminal command

Paste this prompt into Codex:

```text
$skill-installer install https://github.com/OptimistOtaku/Codexter/tree/main/skills/codex-cleanup
```

The built-in installer downloads the full skill folder, including its references and Python helper. It refuses an existing destination. Its location follows that Codex installation's own configuration; do not assume every installer uses the same global directory.

## Alternative: Skills CLI

If you already use Node.js, the maintained Skills CLI provides another one-command route. Current upstream requires **Node.js 22.20 or newer**.

macOS/Linux:

```sh
npx --yes skills@latest add OptimistOtaku/Codexter --skill codex-cleanup --agent codex --global --copy --yes
```

Windows PowerShell:

```powershell
npx.cmd --yes skills@latest add OptimistOtaku/Codexter --skill codex-cleanup --agent codex --global --copy --yes
```

`npx.cmd` avoids PowerShell script-alias execution-policy problems. The first `--yes` accepts npm's package download; the last accepts skill installation. `--copy` avoids symlink privilege requirements. Review existing installations first, since accepting prompts may replace installed skill files. This third-party installer collects anonymous usage data; its documented `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` setting disables telemetry and audit requests. Use the installer you already trust rather than stacking multiple copies.

These alternative commands were checked against upstream documentation; the automated installation smoke check covers GitHub CLI. Sources: [Skills CLI](https://github.com/vercel-labs/skills), [options](https://github.com/vercel-labs/skills/blob/main/docs/commands.md), [configuration](https://github.com/vercel-labs/skills/blob/main/docs/troubleshooting.md).

## Manual fallback

Copy the whole `skills/codex-cleanup` folder from a downloaded or cloned repository into one skill directory supported by your Codex version. Current official docs list `~/.agents/skills` for user skills and `.agents/skills` for project skills. The bundled installer and some existing builds use `~/.codex/skills`. Let an installer choose its supported location whenever practical, and avoid duplicate names across directories.

## Use after installation

Codex loads skill metadata first, then reads full instructions when needed. Invoke `$codex-cleanup` explicitly, or let Codex select it for a matching task. If discovery does not refresh, restart Codex. Installation does not register an unconditional cleanup hook: adopt the optional [end-of-task integration](INTEGRATION.md) if you want routine cleanup guidance.
