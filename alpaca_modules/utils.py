

# General purpose utility functions for
# the different modules.


def pprint(data, indent=2):
  print(json.dumps(data, indent=indent))

def chunk(lst, n):
  return [lst[i:i + n] for i in range(0, len(lst), n)]