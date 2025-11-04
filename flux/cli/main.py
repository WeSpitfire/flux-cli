@cli.command()
@click.argument('query')
def search(query):
    """Search the codebase for a given natural language query."""
    results = search_code(query)
    for result in results['top_matches']:
        print(f"{result['file']}:{result['line']} - {result['code_snippet']}")