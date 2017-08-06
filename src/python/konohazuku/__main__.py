from pathlib import Path
import json
from collections import Counter, defaultdict
import elo
import pandas as pd
import numpy as np
import MySQLdb
from MySQLdb.cursors import DictCursor
from argparse import ArgumentParser


LOGS_DIR = Path("/var/local/logs/")
ROOT_DIR = Path(__file__).absolute().parent.parent.parent.parent


def prob(win, all, draw):
    nall = all - draw
    return win / nall if nall > 0 else 0.


def fetch_results_db():
    try:
        conn = MySQLdb.connect(host="35.194.126.173", user="root", passwd="kaban", db="adlersprung")

        cursor = conn.cursor(DictCursor)
        cursor.execute("SELECT * FROM match_log")
        for row in cursor.fetchall():
            log_data = json.loads(row["log"])
            if "tag_names" not in log_data:
                continue
            all_names = log_data["tag_names"]
            if "scores" not in log_data:
                continue
            raw_scores = [-1] * len(all_names)
            for sc in log_data["scores"]:
                raw_scores[sc["punter"]] = sc["score"]
            rank_scores = [len([s for s in raw_scores if s <= score]) for score in raw_scores]
            punter_rank_scores = defaultdict(list)
            for name, rank_score in zip(all_names, rank_scores):
                punter_rank_scores[name].append(rank_scores)
            print(punter_rank_scores)
            yield punter_rank_scores
    finally:
        conn.close()


def fetch_results_file():
    for meta_path in LOGS_DIR.iterdir():
        if not meta_path.name.endswith("meta.json"):
            continue
        with meta_path.open() as f:
            meta_json = json.load(f)
        punter_rank_scores = defaultdict(list)
        if "tag_names" not in meta_json:
            continue
        all_names = meta_json["tag_names"]
        if "scores" not in meta_json:
            continue
        for sc in meta_json["scores"]:
            punter_rank_scores[all_names[sc["punter"]]].append(sc["rank_score"])
        yield punter_rank_scores


def fetch_results(punter_rank_score_collection):
    for punter_rank_scores in punter_rank_score_collection:
        if len(punter_rank_scores) != 2:
            continue
        names = list(punter_rank_scores.keys())
        if [name for name in names if len(name) == 40]:
            print(names)
            print("seems to be commit hash. skipping")
            continue
        scores = [np.average(punter_rank_scores[name]) for name in names]
        yield names, scores


def main():
    parser = ArgumentParser()
    parser.add_argument("--use-db", action="store_true", help="Use Japari Library (MySQL DB)")
    args = parser.parse_args()

    print("meta analysis tool konohazuku")
    if args.use_db:
        print("using database")
        data_source = fetch_results_db()
    else:
        print("using file system data")
        data_source = fetch_results_file()
    kati = Counter()
    draws = Counter()
    per_win_agg = Counter()
    per_draw_agg = Counter()
    per_match_agg = Counter()
    for names, scores in fetch_results(data_source):
        if scores[0] > scores[1]:
            kati[(names[0], names[1])] += 1
            per_win_agg[names[0]] += 1
        elif scores[1] > scores[0]:
            kati[(names[1], names[0])] += 1
            per_win_agg[names[1]] += 1
        else:
            draws[(names[0], names[1])] += 1
            draws[(names[1], names[0])] += 1
            per_draw_agg[names[0]] += 1
            per_draw_agg[names[1]] += 1
        per_match_agg[names[0]] += 1
        per_match_agg[names[1]] += 1
    all_names = list(per_match_agg.keys())
    win_matrix = [[kati[(winner, loser)] for loser in all_names] for winner in all_names]
    ratings = list(elo.estimate_rating(win_matrix))
    name2ratings = {name: rating for name, rating in zip(all_names, ratings)}
    all_names.sort(key=lambda name: name2ratings[name], reverse=True)
    data_table = []
    index = []
    for name in all_names:
        win, all, draw = per_win_agg[name], per_match_agg[name], per_draw_agg[name]
        nall = all - draw
        header = "{}: Rating: {:.3}, {:.2f}% ({} / {}, draw: {})".format(name.strip(), name2ratings[name], prob(win, all, draw) * 100, win, nall, draw)
        print(header)
        index.append(header)
        row = []
        for opponent in all_names:
            win, lose = kati[(name, opponent)], kati[(opponent, name)]
            nall = win + lose
            draw = draws[(name, opponent)]
            all = nall + draw
            column = "{:.2f}% ({} / {}, draw: {})".format(prob(win, all, draw) * 100, win, nall, draw)
            print(column)
            row.append(column)
        data_table.append(row)
    df = pd.DataFrame(data_table, index=index, columns=index)
    publish_dir = Path(ROOT_DIR / "reports")
    if not publish_dir.exists():
        publish_dir.mkdir()
    html_dir = publish_dir / "index.html"
    with html_dir.open("w") as file:
        file.write(df.to_html())

    artifact_dir = Path(ROOT_DIR / "konoha_artifacts")
    if not artifact_dir.exists():
        artifact_dir.mkdir()
    artifact_path = Path(artifact_dir / "ratings.json")
    artifact_data = {name: {
        "rating": name2ratings[name],
        "match_count": per_match_agg[name]
    } for name in all_names}
    with artifact_path.open("w") as f:
        json.dump(artifact_data, f)


if __name__ == '__main__':
    main()