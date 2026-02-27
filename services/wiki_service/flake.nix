{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      supportedSystems =
        [ "x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python312;

          runtimeLibs = [ pkgs.stdenv.cc.cc.lib ];
        in {
          default = pkgs.mkShellNoCC {
            packages =
              [ python python.pkgs.virtualenv python.pkgs.pip pkgs.zsh ]
              ++ runtimeLibs;

            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath runtimeLibs;

            shellHook = ''
              VENV_DIR=".venv"

              if [ ! -x "$VENV_DIR/bin/python" ]; then
                echo "[devShell] creating virtualenv at $VENV_DIR"
                ${python.pkgs.virtualenv}/bin/virtualenv "$VENV_DIR" >/dev/null
              fi

              . "$VENV_DIR/bin/activate"

              if [ -z "''${SKIP_PIP_INSTALL-}" ]; then
                echo "[devShell] pip install -e ."
                python -m pip install -e .
              fi

              case "$-" in
                *i*)
                  if [ -z "''${ZSH_VERSION-}" ]; then
                    exec ${pkgs.zsh}/bin/zsh
                  fi
                  ;;
              esac
            '';
          };
        });
    };
}
