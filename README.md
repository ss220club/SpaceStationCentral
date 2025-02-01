# Space Station Central

API для объеденения множества серверов SS13 и SS14 в одну систему. Позволяет получить информацию о игроках, сервере, банах и т.д.
В теории можно использовать для других целей, например, как бэкенд для мифического сайта, если подвергнуть мелким доработкам.

## Конфиг

Конфиг берется по пути `./.config.toml`. Пример можно посмотреть в файле `./config_example.toml`.
Конфиг логов берется по пути `./log_config.yaml`.

## Запуск

```sh
docker run -v $(pwd)/.config.toml:/.config.toml:ro \
           -v $(pwd)/logs:/logs \
           --add-host=host.docker.internal:host-gateway \
           -d \
           -p 8000:8000 \
           --name SpaceStationCentral \
           ghcr.io/ss220club/spacestationcentral:latest
```
