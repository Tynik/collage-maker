import os
import zmq
import time
import json
import random
import typing
import logging
import requests
import threading

from requests.adapters import HTTPAdapter

from PIL import Image, ImageDraw
from github import Github, GithubException

from . import settings


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Task(threading.Thread):
    def __init__(self, queue, check_queue_time: int = .0001, zmq_context=None, kwargs=None):
        self._zmq_context = zmq_context or zmq.Context()
        self._queue = queue
        self._check_queue_time = check_queue_time
        self._running = True
        super(Task, self).__init__(kwargs=kwargs)

    def start(self) -> 'Task':
        super(Task, self).start()
        return self

    def run(self) -> None:
        with self._zmq_context.socket(zmq.DEALER) as socket:
            socket.setsockopt(zmq.IDENTITY, self._queue.encode())
            socket.connect('ipc://routing.ipc')

            while self._running:
                try:
                    self.on_message(socket, socket.recv_json())
                except Exception as e:
                    logging.error(e, exc_info=True)
                finally:
                    pass

                time.sleep(self._check_queue_time)

    def stop(self) -> None:
        self._running = False

    def on_message(self, socket, params):
        raise NotImplementedError


class TasksList:
    def __init__(self, queue, zmq_context=None):
        self._queue = queue
        self._zmq_context = zmq_context or zmq.Context()
        self._list = []

    def add(self, task, kwargs=None) -> None:
        self._list.append(task(self._queue, zmq_context=self._zmq_context, kwargs=kwargs))

    def start(self) -> None:
        for task in self._list:
            task.start()

    def stop(self) -> None:
        for task in self._list:
            task.stop()


class GitHubRepositoryFinderTask(Task):
    def on_message(self, socket, params):
        git_hub = Github(params['git_hub_key'])
        searched_reps = git_hub.search_repositories(params['q'])[:self._kwargs['search_reps_limit']]
        try:
            for rep in searched_reps:
                contributors = rep.get_contributors()
                total_count = contributors.totalCount
                for cont in contributors:
                    socket.send_json({
                        'rep': rep.name,
                        'cont_id': cont.id,
                        'url': cont.avatar_url,
                        'total_avatars': total_count})

        except GithubException:
            socket.send_json({'error': 'rep_not_found'})


class AvatarLoaderTask(Task):
    def on_message(self, socket, params):
        with requests.Session() as rs:
            rs.mount('http://', HTTPAdapter(max_retries=3))

            avatar_response = rs.get(params['url'], stream=True)
            if avatar_response.status_code != 200:
                socket.send_json({'rep': params['rep'], 'avatar_status': 'error'})
                return

            rep_path = os.path.join(self._kwargs['avatars_path'], params['rep'])
            if not os.path.isdir(rep_path):
                os.mkdir(rep_path)

            avatar_ext = avatar_response.headers['Content-Type'].split('/')[1]
            with open(os.path.join(rep_path, '%s.%s' % (params['cont_id'], avatar_ext)), mode='wb') as f:
                for chunk in avatar_response:
                    f.write(chunk)

            socket.send_json({'rep': params['rep'], 'avatar_status': 'loaded'})


class Collage:
    def __init__(self, *, size: tuple, position_handler: typing.Callable[[tuple, tuple], tuple]):
        self._size = size
        self._position_handler = position_handler
        self._img = Image.new('RGBA', size, (255, 0, 0, 0))

    def add_img(self, new_img):
        x, y = self._position_handler(self._size, new_img.size)
        self._img.paste(new_img, (x, y))

    def save(self, fp, quality: int = 95):
        self._img.save(fp, format='png', quality=quality)


def handle_avatar_image(avatar_path, avatar_size: tuple, margins: tuple):
    new_width, new_height = avatar_size

    avatar_img = Image.open(avatar_path)
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


def rand_img_position_in_rect(canvas_size, img_size):
    return (
        random.randrange(0, canvas_size[0] - img_size[0]),
        random.randrange(0, canvas_size[1] - img_size[1]))


class CollageMakerTask(Task):
    def on_message(self, socket, params):
        collage = Collage(size=self._kwargs['collage_size'], position_handler=self._kwargs['avatar_position_handler'])
        rep_path = os.path.join(self._kwargs['avatars_path'], params['rep'])

        avatars_number = 0
        for _, _, avatars in os.walk(rep_path):
            avatars_number = len(avatars)
            for avatar in avatars:
                avatar_img = handle_avatar_image(
                    os.path.join(rep_path, avatar),
                    avatar_size=self._kwargs['avatar_size'],
                    margins=self._kwargs['avatar_margins'])

                collage.add_img(avatar_img)

        collage_name = 'collage-%d.png' % avatars_number
        collage.save(os.path.join(rep_path, collage_name), quality=self._kwargs['collage_quality'])

        logging.info('Collage for repository "%s" has been created with a name of "%s"' % (params['rep'], collage_name))


def run():
    git_hub_key = os.environ.get('GIT_HUB_KEY')
    if not git_hub_key:
        raise Exception('You should set GitHub Access Key in `GIT_HUB_KEY` environment variable')

    git_hub_search_query = os.environ.get('GIT_HUB_SEARCH_QUERY')
    if not git_hub_search_query:
        raise Exception('You should set the search query by which you want to find some projects '
                        'in `GIT_HUB_SEARCH_QUERY` environment variable')

    avatars_path = '/tmp/avatars'

    zmq_context = zmq.Context()
    try:
        with zmq_context.socket(zmq.ROUTER) as socket:
            socket.bind('ipc://routing.ipc')

            reps_finder_task = GitHubRepositoryFinderTask(
                'repository_finder_queue',
                zmq_context=zmq_context,
                kwargs={'search_reps_limit': settings.SEARCH_GITHUB_REPOSITORIES_LIMIT}
            ).start()

            avatar_loader_tasks = TasksList('avatar_loader_queue', zmq_context=zmq_context)
            for _ in range(settings.AVATAR_LOADER_TASKS):
                avatar_loader_tasks.add(AvatarLoaderTask, kwargs={'avatars_path': avatars_path})

            avatar_loader_tasks.start()

            collage_maker_tasks = TasksList('collage_maker_queue', zmq_context=zmq_context)
            for _ in range(settings.COLLAGE_MAKER_TASKS):
                collage_maker_tasks.add(
                    CollageMakerTask,
                    kwargs={
                        'avatars_path': avatars_path,
                        'collage_size': (800, 500),
                        'avatar_size': (64, 64),
                        'avatar_margins': (7, 7),
                        'collage_quality': 95,
                        'avatar_position_handler': rand_img_position_in_rect})

            collage_maker_tasks.start()

            params = {'q': git_hub_search_query, 'git_hub_key': git_hub_key}
            socket.send_multipart(['repository_finder_queue'.encode(), json.dumps(params).encode()])

            repositories = {}
            while True:
                out_queue, task_raw_response = socket.recv_multipart()
                out_queue = out_queue.decode()
                task_response = json.loads(task_raw_response)

                if task_response.get('error'):
                    pass
                else:
                    if out_queue == 'repository_finder_queue':
                        repositories.setdefault(task_response['rep'], {
                            'total_avatars': task_response['total_avatars'],
                            'successfully_loaded_avatars': 0,
                            'not_loaded_avatars': 0})

                        socket.send_multipart(['avatar_loader_queue'.encode(), json.dumps(task_response).encode()])

                    elif out_queue == 'avatar_loader_queue':
                        rep = repositories[task_response['rep']]
                        if task_response['avatar_status'] == 'loaded':
                            rep['successfully_loaded_avatars'] += 1
                        else:
                            rep['not_loaded_avatars'] += 1

                        if rep['successfully_loaded_avatars'] + rep['not_loaded_avatars'] == rep['total_avatars']:
                            socket.send_multipart(['collage_maker_queue'.encode(), json.dumps(task_response).encode()])

                time.sleep(.0001)

    except KeyboardInterrupt as e:
        pass

    except Exception as e:
        logging.error(e, exc_info=True)

    finally:
        reps_finder_task.stop()
        avatar_loader_tasks.stop()
        collage_maker_tasks.stop()


if __name__ == '__main__':
    run()
