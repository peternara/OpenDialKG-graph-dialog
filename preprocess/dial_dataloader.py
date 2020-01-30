import json
import csv
import configparser
import sys
import os
from tqdm import tqdm

from nltk.tokenize import word_tokenize

module_path = os.path.abspath('.')
sys.path.insert(0, module_path)
sys.path.append("../../")

from preprocess.data_reader import load_kg, parse_path_cfg
from preprocess.kg_dataloader import get_kg_DataLoader, get_kg_connection_map, get_two_hops_map

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, random_split


def get_dial_vocab():
    return


def dial_reader(data_type, entity_map, relation_map, triple_list, dial_window_size=0):
    assert data_type in ['train', 'dev', 'test']
    path = parse_path_cfg()
    file_path = path['%s_FILE' % data_type.upper()]
    print('Reading from %s' % file_path, end=' ... ')
    with open(file_path, 'r') as f:
        content = json.load(f)
    print(len(content))

    dataset = []
    for sample in content:
        dialogue = sample['dialogue']
        dial_id = sample['dial_id']
        starting_entities = set()
        previous_sentence = ""
        dialogue_history = []
        for ti, turn in enumerate(dialogue):
            if 'action_id' in turn and turn['action_id'] == 'kgwalk/choose_path':
                kg_path = turn['metadata']['path'][1]
                kg_path_id = [(entity_map[triple[0]], relation_map[triple[1]], entity_map[triple[2]]) for triple in
                              kg_path]
                sample = {'dial-id': dial_id,
                          'sample-id': len(dataset),
                          'starting-entities': list(starting_entities),
                          'previous_sentence': previous_sentence,
                          'dialogue-history': dialogue_history[-dial_window_size:],
                          'kg-path-id': kg_path_id}
                if ti != 0:  # there are few samples where assistant chooses path from scratch, I discarded these turns.
                    dataset.append(sample)
                for triple in kg_path:
                    if len(starting_entities) != 0:
                        if not triple[0] in starting_entities:
                            print(json.dumps(dialogue, sort_keys=True, indent=4, separators=(',', ': ')))
                            raise KeyError('%s not found.' % triple[0])
                    # starting_entities.add(triple[0])
                    starting_entities.add(triple[2])
                previous_sentence = turn['metadata']['path'][2]
            elif 'action_id' in turn and turn['action_id'] == 'meta_thread/send_meta_message':  # useless
                previous_sentence = ''
                pass
            else:
                if len(previous_sentence) != 0:
                    dialogue_history = dialogue_history + [previous_sentence]
                # print(turn)
                previous_sentence = turn['message']
            # if 'metadata' in turn and 'action_id' in turn and turn['action_id'] != 'kgwalk/choose_path':
            #     print(json.dumps(dialogue,  sort_keys=True, indent=4, separators=(',', ': ')))
            #     break
    # print(json.dumps(dataset, sort_keys=True, indent=4, separators=(',', ': ')))
    return dataset


class DialDataset(Dataset):
    def __init__(self, dial_dataset):
        self.dial_dataset = dial_dataset

    def __len__(self):
        return len(self.dial_dataset)

    def __getitem__(self, item):
        return self.dial_dataset[item]


class DialDataLoader:
    def __init__(self, dial_dataset: list, batch_size, shuffle):
        self.dial_dataset = dial_dataset
        self.indexes = DataLoader(DialDataset([i for i, _ in enumerate(dial_dataset)]), batch_size=batch_size,
                                  shuffle=shuffle)

    def __len__(self):
        return len(self.dial_dataset)

    def __iter__(self):
        for batch in self.indexes:
            yield [self.dial_dataset[i.item()] for i in batch]

    def __del__(self):
        del self.dial_dataset
        del self.indexes


def get_dial_DataLoader(entity_map, relation_map, triple_list, batch_size):
    train_dataset = dial_reader('train', entity_map, relation_map, triple_list)
    dev_dataset = dial_reader('dev', entity_map, relation_map, triple_list)
    test_dataset = dial_reader('test', entity_map, relation_map, triple_list)
    train = DialDataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    dev = DialDataLoader(dev_dataset, batch_size=batch_size, shuffle=False)
    test = DialDataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    return train, dev, test


if __name__ == '__main__':
    entity_map, relation_map, triple_list = load_kg()
    # WholeDataLoader = get_kg_DataLoader(entity_map, relation_map, triple_list)
    # connection_map = get_kg_connection_map(entity_map, relation_map, triple_list)
    # two_hops_map = get_two_hops_map(connection_map)

    train, dev, test = get_dial_DataLoader(entity_map, relation_map, triple_list, 16)

    print(len(dev))

    cnt = 0
    for di, data in enumerate(dev):
        cnt += len(data)
        # print(data)
        # break
    print(cnt)
