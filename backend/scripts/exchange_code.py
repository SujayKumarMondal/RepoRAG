import asyncio
import sys
sys.path.insert(0, r'D:/SUJAY/Projects/RepoRAG/backend')
from app.services.github.client import GitHubClient

async def run():
    client = GitHubClient()
    try:
        token = await client.exchange_code_for_token('b34f7cad86754cc35a0a')
        print('TOKEN:', token)
    except Exception as e:
        print('ERROR:', e)

if __name__ == '__main__':
    asyncio.run(run())
