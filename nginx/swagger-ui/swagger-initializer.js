window.onload = function() {
  //<editor-fold desc="Changeable Configuration Block">

  // the following lines will be replaced by docker/configurator, when it runs in a docker-container
  window.ui = SwaggerUIBundle({
    url: "/swagger.yaml",
    dom_id: '#swagger-ui',
    deepLinking: true,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIStandalonePreset
    ],
    plugins: [
      SwaggerUIBundle.plugins.DownloadUrl
    ],
    layout: "StandaloneLayout",
  });

  //</editor-fold>
  // 定时检查 swagger.yaml 是否更改
  setInterval(function() {
    fetch("/swagger.yaml")
      .then(response => response.text())
      .then(content => {
        // 比较当前的内容和旧的内容，如果有变化则重新加载 Swagger UI
        if (content !== window.swaggerYamlContent) {
          window.swaggerYamlContent = content;
          ui.specActions.updateSpec(content);  // 重新加载 swagger.yaml 文件
        }
      })
      .catch(err => console.error("Error fetching swagger.yaml:", err));
  }, 3000);  // 每 5 秒检查一次
};
