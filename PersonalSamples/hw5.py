from math import pow
from math import pi, e, sqrt
from math import factorial as fact
import numpy as np
print("First analyze the exact bivariate distribution")
def f(m,n):
    lowerBound = max(m + n - 20, 0)
    upperBound = min(m, n)
    total = 0
    if not (0 <= m and m <= 20 and 0 <= n and n <= 20 and lowerBound <= upperBound):
        print("out of bounds m and n returning zero")
        return 0
    for k in range(lowerBound, upperBound + 1): #have to add 1
        numerator = fact(20) *  pow(0.4,k) * pow(.2, m-k) * pow(.2, n-k) * pow(.2, 20 -m -n +k)
        denominator = fact(k) * fact(m - k) * fact(n - k) * fact(20 - m - n + k)
        total += numerator/denominator
    return total


print("for where m = 10 and n = 10: %f" % f(10, 10))
print("for where m = 20 and n = 0: %f" % f(20, 0))
print("for where m= 10 and n = 11: %f" % f(10,11))
ux = 0 #mean X
uy = 0 #mean Y

expectX2 = 0 #E[X^2] = EE n^2 f(m,n)
expectY2 = 0 #E[Y^2] = EE m^2 f(m,n)
expectXY = 0 # E[XY] = EE mn f(m,n)
for m in range(0, 20 + 1):
    for n in range(0, 20 + 1):
        ux += m * f(m, n)
        expectX2 += pow(m, 2) * f(m, n) #n^2 * f(m,n)

        uy += n * f(m, n)
        expectY2 += pow(n, 2) * f(m, n) #y^2 * f(m,n)

        expectXY += m * n * f(m, n) # m*n * f(m,n)

varx = expectX2 - pow(ux, 2) #E[X^2] - ux^2
vary = expectY2 - pow(uy, 2 ) #E[Y^2] - uy^2
stdX = sqrt(varx)
stdY = sqrt(vary)

covar = expectXY - ux* uy #cov = E[X,y] - ux*uy
corr = covar/ (stdX * stdY) #correlation coefficient
print("ux:",ux)
print("uy:",uy)
print("Expectation XY:", expectXY)
print("Expectation X^2:", expectX2)
print("Expectation X^2:", expectY2)
print("covar", covar)
print("varx", varx)
print("vary", vary)
print("stdX", stdX)
print("stdY", stdY)
print("correlation coefficient:",corr)

print("-------------------------------------")
"""The normal pdf approximation"""
print("now analyze the approximate normal bivariate distribution")

@np.vectorize
def pdfNorm(m,n): 
    const = 1 / (2 * pi * stdX * stdY * sqrt(1 - pow(corr, 2))) #constant term at the front
    exponent = -1/ (2 * (1 - pow(corr, 2))) * (pow(m - ux, 2)/ varx - 2 * corr * (m - ux)/ stdX * (n - uy)/ stdY + pow(n - uy,2)/ vary)
    return const * pow(e, exponent)

print("for where m = 10 and n = 10: %f" % pdfNorm(10, 10))

mnDict = {} #(m, n) -> abs(f(m, n) - pdfNorm(m,n))
for n in range(0, 20 + 1):
    for m in range(0, 20 + 1):
        mnDict[(m, n)] = abs(f(m, n) - pdfNorm(m, n))

mnMax = max(mnDict.keys(), key = lambda  x: mnDict[x])
mnMaxDiff = mnDict[mnMax]
print("The max Difference is at m = %d n = %d with a difference of %f" % (mnMax[0], mnMax[1], mnMaxDiff))


"""print countor lines"""
from matplotlib import pylab as plt
plt.figure()
x = np.arange(0, 20, .1)
y = np.arange(0, 20, .1)
X, Y = np.meshgrid(x, y) #X, Y are all possible pairings in coordinate space
X = X.T
Y = Y.T
Z = pdfNorm(X, Y)
plt.contour(X,Y, Z) #default contour function in matplotlib

plt.plot(ux, uy, "bo") #label ux, uy

plt.xlabel("m")
plt.ylabel("n")
plt.title("Contour plot for Approximate Normal Bivariate Distribution")
plt.show()


#randomly sampl from distribution
import random