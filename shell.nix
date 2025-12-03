{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python312
    python312Packages.tkinter
    python312Packages.pillow
  ];

  shellHook = ''
    echo "Python environment with tkinter and Pillow activated!"
    echo "Run: python bbox_adjuster.py"
  '';
}
