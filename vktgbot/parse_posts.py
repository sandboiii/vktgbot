import re
from typing import Union

from loguru import logger

from api_requests import get_video_url, get_document_data
from config import ConfigParameters
from tools import add_urls_to_text, prepare_text_for_html, prepare_text_for_reposts, reformat_vk_links


async def parse_post(
    item: dict, repost_exists: bool, item_type: str, group_name: str, config: ConfigParameters, config_name: str
) -> dict:
    """
    Parse post text and attachments, prepare them for posting
    to Telegram and return a dict with all the data.

    Args:
        item (dict): Post data from VK API.
        repost_exists (bool): True if post contains a repost.
        item_type (str): Type of post: "post" or "repost".
        group_name (str): Name of group.
        config (ConfigParameters): Config parameters.
        config_name (str): Name of section in config.

    Returns:
        dict: Dict with prepared text and attachments.
    """
    text = prepare_text_for_html(item["text"])
    if repost_exists:
        text = prepare_text_for_reposts(text, item, item_type, group_name)

    text = reformat_vk_links(text)

    urls: list = []
    videos: list = []
    photos: list = []
    docs: list = []

    if "attachments" in item:
        await parse_attachments(item["attachments"], text, urls, videos, photos, docs, config, config_name)

    text = add_urls_to_text(text, urls, videos)
    logger.info(f"{config_name} - {item_type.capitalize()} parsing is complete.")
    return {"text": text, "photos": photos, "docs": docs}


async def parse_attachments(
    attachments, text, urls, videos, photos, docs, config: ConfigParameters, config_name: str
) -> None:
    """Parse attachments and add them to the corresponding lists.

    Args:
        attachments (_type_): Attachments of post.
        text (_type_): Text of post.
        urls (_type_): List of URLs.
        videos (_type_): List of videos.
        photos (_type_): List of photos.
        docs (_type_): List of docs.
        config (ConfigParameters): Config parameters.
        config_name (str): Name of section in config.
    """
    for attachment in attachments:
        if attachment["type"] == "link":
            url = get_url(attachment, text)
            if url:
                urls.append(url)
        elif attachment["type"] == "video":
            video = await get_video(attachment, config)
            if video:
                videos.append(video)
        elif attachment["type"] == "photo":
            photo = get_photo(attachment)
            if photo:
                photos.append(photo)
        elif attachment["type"] == "doc":
            doc = await get_doc(attachment["doc"], config_name)
            if doc:
                docs.append(doc)


def get_url(attachment: dict, text: str) -> Union[str, None]:
    url = attachment["link"]["url"]
    return url if url not in text else None


async def get_video(attachment: dict, config: ConfigParameters) -> str:
    """Get video URL.

    Args:
        attachment (dict): Video attachment.
        config (ConfigParameters): Config parameters.

    Returns:
        str: Video URL.
    """
    owner_id = attachment["video"]["owner_id"]
    video_id = attachment["video"]["id"]
    video_type = attachment["video"]["type"]
    access_key = attachment["video"].get("access_key", "")

    video = await get_video_url(config, owner_id, video_id, access_key, config_name)
    if video:
        return video
    elif video_type == "short_video":
        return f"https://vk.com/clip{owner_id}_{video_id}"
    else:
        return f"https://vk.com/video{owner_id}_{video_id}"


def get_photo(attachment: dict) -> Union[str, None]:
    """Get photo URL.

    Args:
        attachment (dict): Photo attachment.

    Returns:
        Union[str, None]: Photo URL.
    """
    sizes = attachment["photo"]["sizes"]
    types = ["w", "z", "y", "x", "r", "q", "p", "o", "m", "s"]

    for type_ in types:
        if next(
            (item for item in sizes if item["type"] == type_),
            False,
        ):
            return re.sub(
                "&([a-zA-Z]+(_[a-zA-Z]+)+)=([a-zA-Z0-9-_]+)",
                "",
                next(
                    (item for item in sizes if item["type"] == type_),
                    False,
                )["url"],
            )
    else:
        return None


async def get_doc(doc: dict, config_name: str) -> Union[dict, None]:
    """Get doc and save it to the temp folder.

    Args:
        doc (dict): Doc attachment.
        config_name (str): Name of section in config.

    Returns:
        Union[dict, None]: Dict with doc name, url and path to it.
    """
    if doc["size"] > 50000000:
        logger.info(
            f"{config_name} - The document was skipped due to its size exceeding the 50MB limit: {doc['size']=}."
        )
        return None
    else:
        with open(f'./temp/{config_name}/{doc["title"]}', "wb") as file:
            file.write(await get_document_data(doc["url"]))

    return {"title": doc["title"], "url": doc["url"]}
