{
  description = "iagitup";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-unstable";
    mach-nix.url = "github:DavHau/mach-nix";
    mach-nix.inputs.nixpkgs.follows = "nixpkgs";
    # dream2nix.url = "github:nix-community/dream2nix";
    # nixpkgs.follows = "dream2nix/nixpkgs";
  };

  outputs = { self, mach-nix, nixpkgs }: {
    devShells.x86_64-linux.default = mach-nix.lib.x86_64-linux.mkPythonShell {
      ignoreDataOutdated = true;
      python = "python312";
      requirements = ''
        setuptools
        internetarchive
        git
      '';
    };
  };
}
