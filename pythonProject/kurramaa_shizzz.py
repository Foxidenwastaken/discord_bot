import aiohttp
import asyncio
import json

BASE_URL = "https://api.beatleader.com/"

async def fetch_player_scores(session, player_id, page, count, order="asc", time_from=0):
    """Fetches one page of player scores from BeatLeader"""
    url = f"{BASE_URL}player/{player_id}/scores?sortBy=date&order={order}&page={page}&count={count}&time_from={time_from}"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
    except Exception as e:
        print(f"error fetching scores: {e}")
        return None


async def fetch_all_player_scores(player_id, time_from=0):
    """Fetches *all* scores of a player uwu"""
    page = 1
    COUNT = 100
    all_scores = []

    async with aiohttp.ClientSession() as session:
        response = await fetch_player_scores(session, player_id, page, COUNT, "asc", time_from)
        if not response:
            return None

        total = response.get("metadata", {}).get("total", 0)
        print(f"total scores: {total}")

        while response and response.get("data"):
            all_scores.extend(response["data"])
            page += 1
            response = await fetch_player_scores(session, player_id, page, COUNT, "asc", time_from)

    return all_scores


# example use (run it in async context)
# asyncio.run(fetch_all_player_scores(76561198268484550))
