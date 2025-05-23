import re, string
def pythonify_string(s):
  ret = ""
  for char in s:
    if char in string.ascii_letters or char in string.digits or \
        char in string.punctuation or char.isspace():
      ret += char
    else:
      ret += '\\0' + oct(ord(char))[2:]
  return ret

def remove_escape_sequences(text):
    """Removes any terminal escape sequences from a string"""
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', text)


def unicode_replacement(match):
  return '\\u{:04x}'.format(ord(match.group(0)))

def escape_unicode(text):
  return re.sub(r'[^\x0d\x0a\x20-\x7E]', unicode_replacement, text)

