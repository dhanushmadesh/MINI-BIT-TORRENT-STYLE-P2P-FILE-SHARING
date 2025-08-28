# gen_meta.py — simple .p2pmeta generator
import os, sys, json, hashlib, argparse

def sha1_chunks(path, piece_size=256*1024):
    pieces = []
    with open(path, "rb") as f:
        while True:
            chunk = f.read(piece_size)
            if not chunk:
                break
            pieces.append(hashlib.sha1(chunk).hexdigest())
    return pieces

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file_path", help="Path to the file (e.g., samples/7TH SEM SYLLABUS.pdf)")
    ap.add_argument("--piece-size", type=int, default=256*1024, help="Piece size in bytes (default 256 KiB)")
    ap.add_argument("--tracker", default="http://127.0.0.1:6969", help="Tracker URL")
    args = ap.parse_args()

    file_path = args.file_path
    if not os.path.isfile(file_path):
        sys.exit(f"File not found: {file_path}")

    name = os.path.basename(file_path)
    length = os.path.getsize(file_path)
    pieces = sha1_chunks(file_path, args.piece_size)

    meta = {
        "name": name,
        "length": length,
        "pieceLength": args.piece_size,   # ✅ fixed key
        "pieces": pieces,
        "tracker": args.tracker
    }



    meta_path = file_path + ".p2pmeta"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✅ Metadata file created: {meta_path}")

if __name__ == "__main__":
    main()
