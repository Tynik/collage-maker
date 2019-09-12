<template>
  <div style="height: 100%">
    <input id="github-key" v-model="gitHubKey" placeholder="Please type the GitHub access key">
    <input id="search-input" v-model="searchQuery" placeholder="Please type the search query of GitHub API">

    <button id="search-button"
      @click="makeCollage"
      :disabled="!gitHubKey || !searchQuery || makingCollageProcess">Make a collage</button>

    <div id="collage-container">
      <div id="collage-info" v-show="collageData">
        <span class="name">Avatars:</span><span class="value">{{collageInfo.avatars_number}}</span>
      </div>
      <img id="collage" :src="collageData" v-show="collageData">
      <div class="spinner" v-show="makingCollageProcess"></div>
      <div class="errors">
        <div class="error" v-for="error in errors">{{error}}</div>
      </div>
    </div>
  </div>
</template>

<script>
    export default {
        data() {
            return {
                searchQuery: 'apple',
                gitHubKey: '',
                collageData: null,
                collageInfo: {
                    avatars_number: null
                },
                makingCollageProcess: false,
                errors: []
            }
        },
        methods: {
            makeCollage() {
                const opts = {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-GitHub-Access-Key': this.gitHubKey
                    },
                    body: JSON.stringify({ q: this.searchQuery, size: [900, 600] })
                };
                this.errors = [];
                this.collageData = null;
                this.makingCollageProcess = true;

                fetch('http://127.0.0.1:8787/collage/', opts)
                    .then((response) => response.json())
                    .then(this.checkMakeCollageStatus)
                    .catch(() => {})
            },
            checkMakeCollageStatus ({ id }) {
                let opts = {headers: {'Content-Type': 'application/json'}};
                fetch(`http://127.0.0.1:8787/collage/${id}/status/`, opts)
                    .then((response) => response.json())
                    .then((data) => {
                        console.log(data);
                        if (data.status === 'in_progress') {
                            setTimeout(this.checkMakeCollageStatus.bind(null, { id }), 1000)

                        } else if (data.status === 'done') {
                            this.getCollageInfo(id)
                                .then(({ avatars_number }) => {
                                    this.collageInfo.avatars_number = avatars_number
                                });

                            this.getCollage(id)
                                .then((collageData) => { this.collageData = collageData })
                                .finally(() => {this.makingCollageProcess = false; })

                        } else if (data.status === 'error') {
                            this.errors.push('Something went wrong...');
                            this.makingCollageProcess = false;
                        }
                    })
                    .catch(() => { this.makingCollageProcess = false; });
            },
            getCollage(id) {
                return fetch(`http://127.0.0.1:8787/collage/${id}/`)
                    .then(response => response.arrayBuffer())
                    .then(buffer => `data:image/png;base64,${this.arrayBufferToBase64(buffer)}`)
                    .catch(() => {})
            },
            getCollageInfo(id) {
                let opts = {headers: {'Content-Type': 'application/json'}};
                return fetch(`http://127.0.0.1:8787/collage/${id}/info/`, opts)
                    .then((response) => response.json())
                    .catch(() => {})
            },
            arrayBufferToBase64 (buffer) {
                let binary = '';
                let bytes = [].slice.call(new Uint8Array(buffer));
                bytes.forEach((b) => binary += String.fromCharCode(b));
                return window.btoa(binary);
            }
        }
    }
</script>

<style lang="scss" scoped>
  #github-key, #search-input {
    width: 33%;
    font-size: 1.3em;
    text-align: center;
  }

  #search-button {
    font-size: 1.3em;
    cursor: pointer;
    border: none;
    border-radius: 4px;
    box-shadow: 0 2px 5px 0 rgba(0, 0, 0, 0.26);
    padding: 5px 10px;
  }

  #collage {
    margin: 20px auto;
    display: block;
  }

  #collage-container {
    height: 100%;
  }

  #collage-info {
    margin-top: 10px;

    .name {
      font-weight: bold;
    }
    .value {
      margin-left: 5px;
    }
  }

  .spinner {
    position: relative;
    top: 50%;
    transform: translateY(-50%);
    margin: 0 auto;
    width: 96px;
    height: 96px;
    background: url("spinner.gif") no-repeat;
    background-size: 96px 96px;
  }

  .errors {
    position: relative;
    top: 50%;
    transform: translateY(-50%);
    color: #804947;
    font-size: 1.3em;
  }
</style>