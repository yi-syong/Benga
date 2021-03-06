from __future__ import absolute_import, unicode_literals

import os
import pandas as pd
import shutil
from celery import shared_task
from django.conf import settings
from django.core.files import File

from dendrogram.serializers import DendrogramSerializer
from dendrogram.models import Batch
from src.algorithms import clustering


def read_profiles(input_dir):
    files = list(filter(lambda x: x.endswith(".tsv"), os.listdir(input_dir)))
    if len(files) == 1:
        return pd.read_csv(os.path.join(input_dir, files[0]), sep="\t", index_col=0)
    else:
        profiles = []
        for filename in files:
            p = pd.read_csv(os.path.join(input_dir, filename), sep="\t", index_col=0)
            profiles.append(p)
        return pd.concat(profiles, axis=1, sort=False)


def plot(input_dir, output_dir, linkage):
    profiles = read_profiles(input_dir)
    dendrogram = clustering.Dendrogram(profiles, linkage)
    dendrogram.cluster(show_node_info=True)
    newick_filename = os.path.join(output_dir, "dendrogram.newick")
    dendrogram.to_newick(newick_filename)
    pdf_filename = os.path.join(output_dir, "dendrogram.pdf")
    dendrogram.figure.savefig(pdf_filename)
    svg_filename = os.path.join(output_dir, "dendrogram.svg")
    dendrogram.figure.savefig(svg_filename)
    png_filename = os.path.join(output_dir, "dendrogram.png")
    dendrogram.figure.savefig(png_filename)
    return newick_filename, pdf_filename, png_filename, svg_filename


def save(batch_id, linkage, newick_filename, pdf_filename, png_filename, svg_filename):
    dendrogram_data = {
        "id": batch_id, "linkage": linkage,
        "png_file": File(open(png_filename, "rb")),
        "pdf_file": File(open(pdf_filename, "rb")),
        "svg_file": File(open(svg_filename, "rb")),
        "newick_file": File(open(newick_filename, "rb")),
    }
    serializer = DendrogramSerializer(data=dendrogram_data)
    if serializer.is_valid():
        serializer.save()
    else:
        print(serializer.errors)


def get_prof_number(batch_id):
    return Batch.objects.get(pk=batch_id).prof_num


def get_linkage(batch_id):
    return Batch.objects.get(pk=batch_id).linkage


def get_file_number(dir, ext=".tsv"):
    return len(list(filter(lambda x: x.endswith(ext), os.listdir(dir))))


@shared_task
def plot_dendrogram(batch_id):
    input_dir = os.path.join(settings.MEDIA_ROOT, "uploads", batch_id)
    output_dir = os.path.join(settings.MEDIA_ROOT, "temp", batch_id)
    os.umask(0)
    os.makedirs(output_dir, exist_ok=True)
    prof_num = get_prof_number(batch_id)
    if prof_num == get_file_number(input_dir):
        linkage = get_linkage(batch_id)
        newick_file, pdf_file, png_file, svg_file = plot(input_dir, output_dir, linkage)
        save(batch_id, linkage, newick_file, pdf_file, png_file, svg_file)
        shutil.rmtree(output_dir)
