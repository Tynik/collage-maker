import io
import zmq
import uuid
import time
import base64
import random
import typing
import logging
import requests
import threading
import functools

from PIL import Image, ImageDraw
from github import Github

from .threads import TasksList
from . import settings


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

_REGISTERED_COMMAND_FUNCTIONS = {}
_COLLAGES = {}


class Collage:
    __slots__ = ('_x', '_y', '_img', '_size')

    def __init__(self, *, size: tuple):
        self._size = size
        self._img = Image.new('RGBA', size, (255, 0, 0, 0))

    def add_img(self, new_img):
        x = random.randrange(0, self._size[0] - new_img.size[0])
        y = random.randrange(0, self._size[1] - new_img.size[1])
        self._img.paste(new_img, (x, y))

    def save(self) -> io.BytesIO:
        output = io.BytesIO()
        self._img.save(output, format='png', quality=95)
        output.seek(0)
        return output


def handle_avatar_image_size(
    min_avatar_size: tuple, max_avatar_size: tuple, total_commits: int, max_total_commits: int
):
    new_width = min_avatar_size[0] + (
        max_avatar_size[0] - min_avatar_size[0]) * int(total_commits / max_total_commits)
    new_height = min_avatar_size[1] + (
        max_avatar_size[0] - min_avatar_size[1]) * int(total_commits / max_total_commits)

    return new_width, new_height


def handle_avatar_image(img_data, margins: tuple, avatar_image_size_handler):
    new_width, new_height = avatar_image_size_handler()

    avatar_img = Image.open(img_data)
    avatar_img.thumbnail((new_width, new_height))

    avatar_img_with_margins = Image.new('RGB', (
        new_width + margins[0] * 2, new_height + margins[1] * 2), (255, 255, 255))

    # draw borders over the avatar
    draw = ImageDraw.Draw(avatar_img_with_margins)
    draw.rectangle((
            # x
            (0, 0),
            # y
            (new_width + margins[0] * 2 - 1, new_height + margins[1] * 2 - 1)),
        outline=(76, 76, 76), width=1)

    avatar_img_with_margins.paste(avatar_img, margins)
    return avatar_img_with_margins


def fetch_avatars(*, contributors_stats, max_fetch_avatars_per_thread: int, handler: callable, timeout=60):
    def loader(*, stats_chunk: typing.List[tuple]):
        for avatar_url, total_commits in stats_chunk:
            img_response = requests.get(avatar_url, stream=True)
            if img_response.status_code != 200:
                continue

            handler(img_data=img_response.raw, total_commits=total_commits)

    tasks = TasksList()
    stats_chunks = divide_chunks(contributors_stats, max_fetch_avatars_per_thread)
    for stats_chunk in stats_chunks:
        tasks.add(target=loader, kwargs={'stats_chunk': stats_chunk}).start()

    tasks.wait(timeout=timeout)


class ContributorsStats:
    def __init__(self, repositories, threads_number=1):
        self._repositories = repositories
        self._threads_number = threads_number
        self._result = []

    def fetch(self, timeout=60):
        tasks = TasksList()
        for reps_chunk in divide_chunks(self._repositories, self._threads_number):
            tasks.add(target=self._fetch_stats_contributors, args=(reps_chunk, self._result)).start()

        tasks.wait(timeout=timeout)

    def get_result(self):
        return self._result

    result = property(get_result)

    def get_max_total_commits(self):
        return max(self._result, key=lambda stat: stat[1])[1]

    max_total_commits = property(get_max_total_commits)

    def _fetch_stats_contributors(self, repositories: list, result: list):
        for rep in repositories:
            for cont_stats in rep.get_stats_contributors():
                result.append((cont_stats.author.avatar_url, cont_stats.total))


def make_collage(collage_id: str, *, git_hub_key: str, q: str, size: tuple):
    collage = Collage(size=size)
    _COLLAGES[collage_id] = {'status': 'in_progress', 'collage': collage}
    try:
        git_hub = Github(git_hub_key)
        searched_reps = list(git_hub.search_repositories(q)[:settings.MAX_FETCH_REPOSITORIES_NUMBER])

        contributors_stats = ContributorsStats(
            searched_reps,
            threads_number=settings.MAX_HANDLE_REPOSITORIES_PER_THREAD)

        contributors_stats.fetch()

        avatar_image_size_handler = functools.partial(
            handle_avatar_image_size,
            min_avatar_size=(64, 64),
            max_avatar_size=(128, 128),
            max_total_commits=contributors_stats.max_total_commits)

        def add_avatar_to_collage(*, img_data, total_commits):
            collage.add_img(handle_avatar_image(
                img_data,
                margins=(5, 5),
                avatar_image_size_handler=functools.partial(
                    avatar_image_size_handler,
                    total_commits=total_commits)))

        fetch_avatars(
            contributors_stats=contributors_stats.result,
            max_fetch_avatars_per_thread=settings.MAX_FETCH_AVATARS_PER_THREAD,
            handler=add_avatar_to_collage)

    except Exception as e:
        logging.error(e, exc_info=True)
        _COLLAGES[collage_id]['status'] = 'error'
    else:
        _COLLAGES[collage_id]['status'] = 'done'


def divide_chunks(iterable, count_by) -> iter:
    for i in range(0, len(iterable), count_by):
        yield iterable[i:i + count_by]


def register_command(name):
    def wrap(f):
        _REGISTERED_COMMAND_FUNCTIONS[name] = f
        return f
    return wrap


@register_command(name='make_collage')
def make_collage_command(socket, params):
    collage_id = str(uuid.uuid4())
    threading.Thread(target=make_collage, args=(collage_id,), kwargs=params, daemon=True).start()
    socket.send_json({'status': 'pending', 'id': collage_id})


@register_command(name='make_collage_status')
def make_collage_status_command(socket, params):
    collage = _COLLAGES.get(params['id'])
    if collage is None:
        socket.send_json({'status': 'error', 'code': 'collage_not_found'})
        return

    socket.send_json({'status': collage.get('status', 'pending')})


@register_command(name='get_collage')
def get_collage_command(socket, params):
    collage = _COLLAGES.get(params['id'])
    if collage is None:
        socket.send_json({'status': 'error', 'code': 'collage_not_found'})
        return

    socket.send(base64.b64encode(collage['collage'].save().getvalue()))


def run():
    context = zmq.Context()
    with context.socket(zmq.REP) as socket:
        socket.bind('tcp://*:5555')
        while True:
            message = socket.recv_json()
            cmd = message.get('cmd')
            try:
                if cmd is None:
                    socket.send_json({'status': 'error', 'code': 'command_not_found'})
                    continue

                cmd_func = _REGISTERED_COMMAND_FUNCTIONS.get(cmd)
                if cmd_func is None:
                    socket.send_json({'status': 'error', 'code': 'command_not_found'})
                    continue

                cmd_func(socket, message.get('params', {}))

            except Exception as e:
                logging.error(e, exc_info=True)
                try:
                    socket.send_json({'status': 'error', 'message': e.args and e.args[0] or ''})
                except zmq.error.ZMQError:
                    pass

            time.sleep(.001)


if __name__ == '__main__':
    run()