# titiler-aks

This repository manages deployment of [titiler](https://developmentseed.org/titiler) to AKS.

## Setup

Run the `deploy.sh` script to setup Traefik load balancer with 3 titiler pods.

Run `delete.sh` to cleanup the Kubernetes environment.

## Update titiler Docker image to AKS

Docker image will be deployed to Github Package by [docker-image.yaml](.github/workflows/docker-image.yaml)

Update tag version of `titiler-ask` in `manifest.yml`, then execute the following commands to apply.

```zsh
kubectl config use-context GeoKube01
kubectl config set-context $(kubectl config current-context) --namespace=titiler-dev
kubectl apply -f manifest.yml --namespace titiler-dev
```

## References

- https://medium.com/geekculture/traefik-ingress-on-azure-kubernetes-service-fa498ba7e4b4