kubectl config use-context GeoKube01
kubectl config set-context $(kubectl config current-context) --namespace=titiler-dev

az network vnet create \
    --resource-group undpdpbppssdganalyticsgeo \
    --name titilerAKSVnet \
    --location westeurope \
    --address-prefix "10.1.0.0/16"
az network vnet subnet create \
    --resource-group undpdpbppssdganalyticsgeo \
    --name titilerAKSSubnet \
    --vnet-name titilerAKSVnet \
    --address-prefix "10.1.0.0/22"
az network public-ip create \
    --resource-group undpdpbppssdganalyticsgeo \
    --name titilerAKSPublicIP \
    --location westeurope \
    --allocation-method Static \
    --sku standard

aksidentityprid=$(az aks show --name GeoKube01 --resource-group undpdpbppssdganalyticsgeo | jq -r .identity.principalId)
az role assignment create \
    --role "Network Contributor" \
    --assignee $aksidentityprid \
    --scope /subscriptions/1c766f37-8740-4764-932c-bf96cbb29a39/resourceGroups/undpdpbppssdganalyticsgeo

helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm install traefik-titiler traefik/traefik -f traefik-values.yml -n traefik
helm upgrade traefik-titiler traefik/traefik -f traefik-values.yml -n traefik

kubectl apply -f manifest.yml --namespace titiler-dev
