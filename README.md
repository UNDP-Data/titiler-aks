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

## Deploy Martin

```zsh
$kubectl apply -f manifest.yml --namespace titiler-dev
```

Check public IP of titiler service

```zsh
$kubectl get svc
NAME      TYPE           CLUSTER-IP    EXTERNAL-IP   PORT(S)        AGE
titiler   LoadBalancer   10.0.128.54   20.31.24.74   80:30758/TCP   29s
```

note. If you changed anything for titiler service, public IP will be changed.

- Test

http://20.31.24.74/cog/tiles/6/33/30?url=https://undpngddlsgeohubdev01.blob.core.windows.net/test/Nigeria_set_lightscore_sy_2020_riocog.tif?c3Y9MjAyMS0wNi0wOCZzZT0yMDIyLTA2LTAxVDExJTNBNTglM0ExN1omc3I9YiZzcD1yJnNpZz1hSlJ4eFFOTzhpaHUzWTdXNDc1MnY2UTdEN3R3V0Y2NUglMkI5ZGRBRW83ZTQlM0Q=

## Delete environment

```zsh
$kubectl delete -f manifest.yml --namespace titiler-dev
```