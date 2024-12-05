# Hybrid-SQuAD
A repository for Hybrid-SQuAD: **Hybrid** **S**cholarly **Qu**estion **A**nswering **D**ataset paper.


If you want to test your model please follow the instructions in [Codalab Page](https://codalab.lisn.upsaclay.fr/competitions/19747).

## Resources

The following resources are shared or hosted by us:

[DBLP SPARQL Endpoint](https://dblp-april24.skynet.coypu.org/sparql) (April 2024 snapshot from DBLP)

[SemOpenAlex Endpoint](https://semoa.skynet.coypu.org/sparql)

[Wikipedia Text Sources](https://drive.google.com/file/d/1ISxvb4q1TxcYRDWlyG-KalInSOeZqpyI/view?usp=drive_link)

In case you want to host the KGs on your system, download the triples from the following [Google Drive link](https://drive.google.com/drive/folders/1aYB_n9PdyVxQlfHXO34ZL_siBqYGoPe0?usp=drive_link).

## Evaluation

Codalab computes two metrics when you upload your answers to the test set questions:

1. Exact Match

2. F-score

The evaluation script can be found [here](https://raw.githubusercontent.com/debayan/scholarly-QALD-challenge/main/2024/dataset/qa_eval_em_f1.py).
