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

          py = pkgs.python312.withPackages
            (ps: with ps; [ grpcio-tools grpcio protobuf pip ]);

          runtimeLibs = [ pkgs.stdenv.cc.cc.lib ];
        in {
          default = pkgs.mkShellNoCC {
            packages = [ py ] ++ runtimeLibs;

            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath runtimeLibs;
          };
        });
    };
}
