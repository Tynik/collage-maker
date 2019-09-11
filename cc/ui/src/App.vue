<template>
  <div style="height: 100%">
    <input id="github-key" v-model="gitHubKey" placeholder="Please type the GitHub access key">
    <input id="search-input" v-model="searchQuery" placeholder="Please type a name of any github project">
    <button id="search-button" @click="makeCollage" :disabled="makingCollageProcess">Make a collage</button>
    <div id="collage-container">
      <img id="collage" :src="collageData" v-show="collageData">
      <div class="spinner" v-show="makingCollageProcess"></div>
    </div>
  </div>
</template>

<script>
    export default {
        data() {
            return {
                searchQuery: '',
                gitHubKey: '40367a4217d32dd7d6aa4ab3eacf656b199e645f',
                collageData: null,
                makingCollageProcess: false
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
                    body: JSON.stringify({q: this.searchQuery})
                };
                this.collageData = null;
                this.makingCollageProcess = true;
                fetch('http://127.0.0.1:8787/collage/', opts)
                    .then((response) => response.json())
                    .then(this.checkMakeCollageStatus)
                    .catch(() => {})
            },
            arrayBufferToBase64 (buffer) {
                let binary = '';
                let bytes = [].slice.call(new Uint8Array(buffer));
                bytes.forEach((b) => binary += String.fromCharCode(b));
                return window.btoa(binary);
            },
            checkMakeCollageStatus ({ id }) {
                let opts = {headers: {'Content-Type': 'application/json'}};
                fetch(`http://127.0.0.1:8787/collage/status/${id}/`, opts)
                    .then((response) => response.json())
                    .then((data) => {
                        console.log(data);
                        if (data.status === 'in_progress') {
                            setTimeout(this.checkMakeCollageStatus.bind(null, { id }), 1000)

                        } else if (data.status === 'done') {
                            fetch(`http://127.0.0.1:8787/collage/${id}/`)
                              .then(response => response.arrayBuffer())
                              .then(buffer => {
                                  var base64Flag = 'data:image/jpeg;base64,';
                                  var imageStr = this.arrayBufferToBase64(buffer);

                                  this.collageData = base64Flag + imageStr;
                              })
                              .finally(() => {
                                  this.makingCollageProcess = false;
                              })
                              .catch(() => {})
                        }
                    });
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
</style>