# titiler-aks

This repository manages deployment of [titiler](https://developmentseed.org/titiler) to AKS.

## Setup

- Create `titiler-dev` namespace

```zsh
# creater titiler-dev namespace
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
#set titiler-dev as default namespace
$kubectl config set-context $(kubectl config current-context) --namespace=titiler-dev
```

## Create a static IP address

see [here](https://docs.microsoft.com/en-us/azure/aks/static-ip)

```zsh
# create static public IP for titiler
$az network public-ip create \
    --resource-group undpdpbppssdganalyticsgeo \
    --name titilerAKSPublicIP \
    --sku Standard \
    --allocation-method static
$az network public-ip show --resource-group undpdpbppssdganalyticsgeo --name titilerAKSPublicIP --query ipAddress --output tsv
# the below is static IP generated
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

# The below command need IT to execute (IT already granted GeoKube01 to access)
$az role assignment create \
    --assignee 8edf0602-b9c0-4322-bf34-802e4f3add7d \
    --role "Network Contributor" \
    --scope /subscriptions/1c766f37-8740-4764-932c-bf96cbb29a39/resourceGroups/undpdpbppssdganalyticsgeo
```

## setup traefik

```zsh
$kubectl create ns traefik

$helm repo add traefik https://helm.traefik.io/traefik
# export default traefik setting to yaml
$helm inspect values traefik/traefik > traefik-values.yaml
```

In order to use static public IP generated before, we need to configure following settings in `traefik-values.yaml`.

```diff
service:
  enabled: true
  type: LoadBalancer
  # Additional annotations applied to both TCP and UDP services (e.g. for cloud provider specific config)
-  # annotations: {}
+  annotations:
+    service.beta.kubernetes.io/azure-load-balancer-resource-group: undpdpbppssdganalyticsgeo
  # Additional annotations for TCP service only
  annotationsTCP: {}
  # Additional annotations for UDP service only
  annotationsUDP: {}
  # Additional service labels (e.g. for filtering Service by custom labels)
  labels: {}
  # Additional entries here will be added to the service spec.
  # Cannot contain type, selector or ports entries.
-  # spec: {}
+  spec:
+    loadBalancerIP: "13.81.173.247"
```


```zsh
# update loadBalancerIP in traefik-values.yaml
$helm install traefik-titiler traefik/traefik -f traefik-values.yaml -n traefik
# if update existing traefic
$helm upgrade traefik-titiler traefik/traefik -f traefik-values.yaml -n traefik

# check whether traefik service is working with allocated public IP
$kubectl get svc -n traefik
NAME              TYPE           CLUSTER-IP   EXTERNAL-IP     PORT(S)                      AGE
traefik-titiler   LoadBalancer   10.0.44.36   13.81.173.247   80:31833/TCP,443:32683/TCP   16s

# check traefik pods are working.
$kubectl get pods -n traefik
NAME                               READY   STATUS    RESTARTS   AGE
traefik-titiler-7c586945c8-t87cb   1/1     Running   0          26s

# try to access traefik dashboards (change pod id)
$kubectl port-forward traefik-titiler-7c586945c8-t87cb 9000:9000 -n traefik
# access http://localhost:9000/dashboard/ 
```

## Deploy Titiler

Now, deploy titiler.

```zsh
$kubectl apply -f manifest.yaml --namespace titiler-dev
```

## setup cert-manager

- https://cert-manager.io/docs/installation/helm/#steps
- https://cert-manager.io/docs/configuration/acme/
- https://www.andyroberts.nz/posts/aks-traefik-https/

```zsh
# create namespace for cert-manager
$kubectl create ns cert-manager
# install cert-manager by kubectl
$kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.8.0/cert-manager.yaml
# check whether cert-manager is working well
$kubectl get pods -n cert-manager
NAME                                       READY   STATUS    RESTARTS   AGE
cert-manager-b4d6fd99b-tvflk               1/1     Running   0          13m
cert-manager-cainjector-74bfccdfdf-fn99h   1/1     Running   0          13m
cert-manager-webhook-65b766b5f8-w62nj      1/1     Running   0          13m

# install clusterissuer in titiler-dev
$kubectl apply -f lets-encrypt.yaml -n titiler-dev
# install certificate in titiler-dev
$kubectl apply -f lets-encrypt-cert.yaml -n titiler-dev
```

- troubleshoot

```zsh
# check certificate status. READY should be true (currently there is problem not becoming true)
$kubectl get certificate
NAME                    READY   SECRET                      AGE
titiler.water-gis.com   False   titiler.water-gis.com-tls   11m

# for further information, try following commands.
$kubectl describe certificate
$kubectl describe certificaterequest
$kubectl describe clusterissuer titiler-cert
$kubectl describe certificaterequest titiler.water-gis.com-ntm99
$kubectl describe order titiler.water-gis.com-ntm99-4133340934
$kubectl get challenges
```

For trouble shooting, following cert-manager website can be helpful.

- https://cert-manager.io/docs/faq/troubleshooting/#2-checking-the-certificaterequest
- https://cert-manager.io/docs/faq/acme/#2-troubleshooting-orders

## Install ingressroute

Once cert-manager settings are done, install ingress route.

```zsh
$kubectl apply -f ingress.yaml -n titiler-dev
```

Currently, getting certificate does not succeed, so traefik works with self certificate.

- Test

https://titiler.water-gis.com/cog/tiles/6/33/30?url=https://undpngddlsgeohubdev01.blob.core.windows.net/test/Nigeria_set_lightscore_sy_2020_riocog.tif?c3Y9MjAyMS0wNi0wOCZzZT0yMDIyLTA2LTAxVDExJTNBNTglM0ExN1omc3I9YiZzcD1yJnNpZz1hSlJ4eFFOTzhpaHUzWTdXNDc1MnY2UTdEN3R3V0Y2NUglMkI5ZGRBRW83ZTQlM0Q=

## Delete environment

```zsh
$kubectl delete -f manifest.yaml --namespace titiler-dev
$kubectl delete -f ingress.yaml -n titiler-dev
$kubectl delete -f lets-encrypt-cert.yaml -n titiler-dev
$kubectl delete -f lets-encrypt.yaml -n titiler-dev
$helm uninstall traefik-titiler -n traefik
$kubectl delete -f https://github.com/jetstack/cert-manager/releases/download/v1.8.0/cert-manager.yaml
$kubectl delete ns titiler-dev
$kubectl delete ns cert-manager
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