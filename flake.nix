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
        in {
          default =
            pkgs.mkShellNoCC { packages = [ py pkgs.stdenv.cc.cc.lib ]; };
        });
    };
}
