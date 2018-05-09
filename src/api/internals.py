import datetime
import os
import json
from src.utils import db
from src.algorithms import profiling, phylogeny
from src.utils import files

PROJECT_HOME = os.getcwd()
INDIR = os.path.join(PROJECT_HOME, "input")
OUTDIR = os.path.join(PROJECT_HOME, "output")


def profiling_api(batch_id, database, occr_level):
    input_dir = os.path.join(INDIR, batch_id)
    files.create_if_not_exist(OUTDIR)
    output_dir = os.path.join(OUTDIR, batch_id)
    files.create_if_not_exist(output_dir)
    profiling.profiling(output_dir, input_dir, database, occr_level=occr_level, threads=2)
    profile_created = datetime.datetime.now()

    with open(os.path.join(output_dir, "namemap.json"), "r") as file:
        names = json.loads(file.read())
    profile_filename = os.path.join(output_dir,
                                    "cgMLST_{}_{}_{}.tsv".format(database, occr_level, batch_id[0:8]))
    os.rename(os.path.join(output_dir, "wgmlst.tsv"), profile_filename)
    dendro = phylogeny.Dendrogram()
    dendro.make_tree(profile_filename, names)
    dendro_created = datetime.datetime.now()
    newick_filename = os.path.join(output_dir, "dendrogram_{}.newick".format(batch_id[0:8]))
    dendro.to_newick(newick_filename)
    pdf_filename = os.path.join(output_dir, "dendrogram_{}.pdf".format(batch_id[0:8]))
    dendro.scipy_tree(pdf_filename)
    svg_filename = os.path.join(output_dir, "dendrogram_{}.svg".format(batch_id[0:8]))
    dendro.scipy_tree(svg_filename)
    png_filename = os.path.join(output_dir, "dendrogram_{}.png".format(batch_id[0:8]))
    dendro.scipy_tree(png_filename)

    sql = "INSERT INTO profile (id,created,file,occurrence,database)" \
          "VALUES(:id,:created,:file,:occr,:db);"
    data = {"id": batch_id, "created": profile_created, "file": profile_filename,
            "occr": occr_level, "db": database}
    db.to_sql(sql, data, database="profiling")

    sql = "INSERT INTO dendrogram (id,created,png_file,pdf_file,svg_file,newick_file)" \
          "VALUES(:id,:created,:png,:pdf,:svg,:new);"
    data = {"id": batch_id, "created": dendro_created, "png": png_filename, "pdf": pdf_filename,
            "svg": svg_filename, "new": newick_filename}
    db.to_sql(sql, data, database="profiling")
