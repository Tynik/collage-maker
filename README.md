### Collage of contributors any GitHub project by names coincidence

To start the project please execute the following commands in the console:
```bash
docker-compose build
docker-compose run -e GIT_HUB_KEY="<put-your-git-hub-access-key>" GIT_HUB_SEARCH_QUERY="<search-query>" app
```
The all downloaded avatars for each found project will appear in `avatars` folder.