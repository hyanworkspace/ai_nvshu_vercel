import pickle
from config import Config

def save_dict_to_file(dictionary, filename):
    with open(filename, 'wb') as f:
        pickle.dump(dictionary, f)

def load_dict_from_file(filename):
    with open(filename, 'rb') as f:
        dictionary = pickle.load(f)
    return dictionary

def add_to_dictionary(char, char_3dim):
    dictionary = load_dict_from_file(Config.DICTIONARY_PATH)
    dictionary[char] = char_3dim
    save_dict_to_file(dictionary, Config.DICTIONARY_PATH)