from topic_factory import run
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--import-candidates');a=p.parse_args();run(a.import_candidates)
