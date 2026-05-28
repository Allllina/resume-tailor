import re
import sys

def extract_changelog(tag):
    try:
        with open('CHANGELOG.md', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return ""
    
    # Escape the tag to use in regular expression
    escaped_tag = re.escape(tag)
    # Match ## [tag] (with or without brackets) and any text on the same line,
    # then capture everything until the next ## header or the end of the file.
    pattern = rf"(?i)##\s+\[?{escaped_tag}\]?(?:[^\n]*)\n(.*?)(?=\n##\s+|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_changelog.py <tag>")
        sys.exit(1)
        
    tag = sys.argv[1]
    body = extract_changelog(tag)
    # If the tag starts with 'v' but we didn't find a match, try without 'v'
    if not body and tag.startswith('v'):
        body = extract_changelog(tag[1:])
        
    print(body)
