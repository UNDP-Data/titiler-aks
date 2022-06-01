# titiler-aks

This repository manages deployment of [titiler](https://developmentseed.org/titiler) to AKS.

## Setup

- Create `titiler-dev` namespace

```zsh
$kubectl create namespace titiler-dev
$kubectl get ns
```

- switch to `titiler-dev` namespace

```zsh
# check context
$kubectl config get-contexts
CURRENT   NAME             CLUSTER          AUTHINFO                                          NAMESPACE
*         GeoKube01        GeoKube01        clusterUser_undpdpbppssdganalyticsgeo_GeoKube01   
          undpdpicluster   undpdpicluster   victortile-dev-read-user                          victortile-dev
#switch to GeoKube01 context
$kubectl config use-context GeoKube01

$kubectl config set-context $(kubectl config current-context) --namespace=titiler-dev
```

## Create a static IP address

see [here](https://docs.microsoft.com/en-us/azure/aks/static-ip)

```zsh
$az network public-ip create \
    --resource-group undpdpbppssdganalyticsgeo \
    --name titilerAKSPublicIP \
    --sku Standard \
    --allocation-method static
$az network public-ip show --resource-group undpdpbppssdganalyticsgeo --name titilerAKSPublicIP --query ipAddress --output tsv

13.81.173.247
```

- Create a service using the static IP address


```zsh
$az aks show -g undpdpbppssdganalyticsgeo -n GeoKube01 --query "identity"
{
  "principalId": "8edf0602-b9c0-4322-bf34-802e4f3add7d",
  "tenantId": "b3e5db5e-2944-4837-99f5-7488ace54319",
  "type": "SystemAssigned",
  "userAssignedIdentities": null
}

# The below command need IT to execute
$az role assignment create \
    --assignee 8edf0602-b9c0-4322-bf34-802e4f3add7d \
    --role "Network Contributor" \
    --scope /subscriptions/1c766f37-8740-4764-932c-bf96cbb29a39/resourceGroups/undpdpbppssdganalyticsgeo
```

## Deploy Titiler

```zsh
$kubectl apply -f manifest.yaml --namespace titiler-dev
```

## setup traefik

```zsh
$kubectl create ns traefik

$kubectl apply -f azuredns-config.yaml
$kubectl create secret generic azuredns-config --from-env-file ./credentials.env -n traefik

$helm repo add traefik https://helm.traefik.io/traefik
$helm inspect values traefik/traefik > traefik-values.yaml
# update loadBalancerIP in traefik-values.yaml
$helm install traefik-titiler traefik/traefik -f traefik-values.yaml -n traefik
# if update existing traefic
$helm upgrade traefik-titiler traefik/traefik -f traefik-values.yaml 

$kubectl get svc -n traefik
NAME              TYPE           CLUSTER-IP   EXTERNAL-IP     PORT(S)                      AGE
traefik-titiler   LoadBalancer   10.0.44.36   13.81.173.247   80:31833/TCP,443:32683/TCP   16s

# try to access traefik dashboards
$kubectl get pods -n traefik
NAME                               READY   STATUS    RESTARTS   AGE
traefik-titiler-7c586945c8-t87cb   1/1     Running   0          26s
$kubectl port-forward traefik-titiler-7c586945c8-t87cb 9000:9000 -n traefik
# access http://localhost:9000/dashboard/ 

$kubectl apply -f ingress.yaml -n titiler-dev
```

- Test

http://titiler.water-gis.com/cog/tiles/6/33/30?url=https://undpngddlsgeohubdev01.blob.core.windows.net/test/Nigeria_set_lightscore_sy_2020_riocog.tif?c3Y9MjAyMS0wNi0wOCZzZT0yMDIyLTA2LTAxVDExJTNBNTglM0ExN1omc3I9YiZzcD1yJnNpZz1hSlJ4eFFOTzhpaHUzWTdXNDc1MnY2UTdEN3R3V0Y2NUglMkI5ZGRBRW83ZTQlM0Q=

## Delete environment

```zsh
$helm uninstall traefik-titiler -n traefik
$kubectl delete -f ingress.yaml -n titiler-dev
$kubectl delete -f manifest.yaml --namespace titiler-dev
```

## Check log

```zsh
$kubectl get pods
NAME                      READY   STATUS    RESTARTS   AGE
titiler-7899fd795-hcnzh   1/1     Running   0          27m
titiler-7899fd795-kqstv   1/1     Running   0          27m
titiler-7899fd795-xnlbv   1/1     Running   0          27m

$kubectl logs titiler-7899fd795-hcnzh
$kubectl describe pods titiler-7899fd795-hcnzh
```

## References

I refered the following websites (Note. they are Japanese language)

- https://qiita.com/eternity1984/items/ae6e5684fd7b02aa23e4#6-ingressroute-%E3%81%A7-whoami-%E3%82%92%E5%85%AC%E9%96%8B%E3%81%99%E3%82%8B
- https://qiita.com/eternity1984/items/1f1dce3fcee3ae58d315#traefik-%E5%8D%98%E4%BD%93%E3%81%A7-lets-encrypt-%E3%82%92%E4%BD%BF%E3%81%88%E3%82%8B%E3%82%88%E3%81%86%E3%81%AB%E6%A7%8B%E6%88%90%E3%81%99%E3%82%8B