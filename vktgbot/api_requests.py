import re

import aiohttp
from loguru import logger

from config import ConfigParameters


async def get_data_from_vk(config: ConfigParameters, config_name: str) -> list[dict]:
    logger.info(f"{config_name} - Trying to get posts from VK.")

    match = re.search("^(club|public)(\d+)$", config.vk_domain)
    if match:
        source_param = {"owner_id": "-" + match.groups()[1]}
    else:
        source_param = {"domain": config.vk_domain}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.vk.com/method/wall.get",
            params=dict(
                {
                    "access_token": config.vk_token,
                    "v": config.req_version,
                    "filter": config.req_filter,
                    "count": config.req_count,
                },
                **source_param,
            ),
        ) as response:
            data = await response.json()
    if "response" in data:
        return data["response"]["items"]
    elif "error" in data:
        logger.error(
            f"{config_name} - Error was detected when requesting data from VK: " f"{data['error']['error_msg']}"
        )
    return []


async def get_video_url(
    config: ConfigParameters, owner_id: str, video_id: str, access_key: str, config_name: str
) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.vk.com/method/video.get",
            params={
                "access_token": config.vk_token,
                "v": config.req_version,
                "videos": f"{owner_id}_{video_id}{'' if not access_key else f'_{access_key}'}",
            },
        ) as response:
            data = await response.json()
    if "response" in data:
        return data["response"]["items"][0]["files"].get("external", "")
    elif "error" in data:
        logger.error(f"{config_name} - Error was detected when requesting data from VK: {data['error']['error_msg']}")
    return ""


async def get_group_name(config: ConfigParameters, owner_id, config_name: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.vk.com/method/groups.getById",
            params={
                "access_token": config.vk_token,
                "v": config.req_version,
                "group_id": owner_id,
            },
        ) as response:
            data = await response.json()
    if "response" in data:
        return data["response"][0]["name"]
    elif "error" in data:
        logger.error(f"{config_name} - Error was detected when requesting data from VK: {data['error']['error_msg']}")
    return ""


async def get_document_data(document_url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(document_url) as response:
            return await response.content.read()
