"""Build a tiny MATLAB-v7.3-like trx.mat (cell of object refs) for the smoke test."""
import h5py, numpy as np, sys
def make(path, ntracks=3, T=1800):
    with h5py.File(path, "w") as f:
        g = f.create_group("trx"); refs = f.create_group("#refs#")
        fields = ["t", "global_state", "run", "cast", "stop", "hunch", "back", "roll", "small_motion"]
        for k in fields:
            ds = g.create_dataset(k, (ntracks, 1), dtype=h5py.ref_dtype)
            for i in range(ntracks):
                t = np.arange(T) / 15.0
                v = t if k == "t" else (((t > 30) & (t < 36) & (i % 2 == 0)).astype(float) if k == "roll" else np.zeros(T))
                r = refs.create_dataset(f"{k}{i}", data=v.reshape(1, -1)); ds[i, 0] = r.ref
        s = g.create_dataset("protocol", (1, 1), dtype=h5py.ref_dtype)
        s[0, 0] = refs.create_dataset("proto", data=np.array([ord(c) for c in "r_625nm600uwcm2_30s2X15s30s"], dtype="uint16").reshape(-1, 1)).ref
if __name__ == "__main__": make(sys.argv[1])
