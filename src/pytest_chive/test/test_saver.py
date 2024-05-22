import chive


def test_save_adata(tmp_path):
    import scanpy as sc
    import numpy as np

    X = np.array([[1, 2], [3, 4]])
    adata = sc.AnnData(X=X)
    file = tmp_path / "adata.h5ad"
    chive.IO.save(adata, file)
    adata2 = chive.IO.load(sc.AnnData, file)

    assert np.array_equal(adata2.X, adata.X)
