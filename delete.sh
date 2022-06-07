kubectl delete -f manifest.yaml --namespace titiler-dev
helm uninstall traefik-titiler -n traefik
kubectl delete ns titiler-dev
