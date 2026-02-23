{
  description = "tg_wiki – Telegram Wiki Bot";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        py = pkgs.python3Packages;

        tg_wiki = py.buildPythonPackage {
          pname = "tg_wiki";
          version = "0.1.0";
          src = ./.;
          pyproject = true;
          build-system = with py; [ setuptools wheel ];
          dependencies = with py; [ aiogram python-dotenv aiohttp redis sqlalchemy asyncpg alembic pgvector ];
        };
      in {
        packages.default = tg_wiki;

        devShells.default = pkgs.mkShell {
          packages = [ tg_wiki pkgs.nixpkgs-fmt ];
          shellHook = ''
            if [ -f .env ]; then
              export BOT_TOKEN=$(grep BOT_TOKEN .env | cut -d '=' -f2)
            fi
          '';
        };
      });
}
