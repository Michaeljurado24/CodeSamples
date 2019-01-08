#for style
use strict;
use warnings;

BEGIN {
	sub getPath {
		my $path = $0;
		my @pathList = split(/\//, $path);
		pop @pathList;
		return join "/", @pathList;
	}
	push @INC, getPath();
}

#open (my $fh, ">", "error.txt");
use Data::Dumper;
use Cwd;

use Try::Tiny;
use Time::HiRes qw( time );
use List::MoreUtils qw(first_index);


use saleModules;
use stateModules;

use IO::Handle;
use Finance::Robinhood;

START: #represents logging in and such

my $stockName = "";
#makes sure you enter a stock
if (! $ARGV[0]){
	print "No_Stock_Entered";
	exit 0;
}else{
	$stockName = $ARGV[0];
}


my $rh = Finance::Robinhood->new();

while(!$rh->{"token"}){
	try {
		if ($ARGV[1] && $ARGV[2]){
			$rh->login($ARGV[1], $ARGV[2]);
		}else{
			$rh->login("redacted\@gmail.com", "redacted");
		}
	} catch {
		STDERR->printflush("cannot log in\n");
	};
}


my $instrument = ""; #this can crash infintely
my $bol = 1;
while ($bol) {
	try {
		$instrument = $rh->instrument($stockName);
		$bol = 0;
	} catch {
		STDERR->printflush("cannot access instrument\n");
	};
}
if (!$instrument){
	goto TAKECOMMANDS; #this is so that you can call "isTradeable. ITS NOT"
}

my $lastQuote = "";
$lastQuote = $instrument->quote(); #this is non crashable but it ruins instrument which in turns ruins rh so i have to restart the script if this fails
if (!$lastQuote) {
	goto START;
}
my $start2 = time(); #last quote refresh time

my $account = ""; 
my $portfolio = "";
#this can crash infintely
while (1) {
	$account = $rh->accounts()->{results}[0];
	if ($account) {
		$portfolio = $account->portfolio();
	}
	($portfolio) ? last : STDERR->printflush("cannot access portfolio\n");
}
#$port$portfolio->refresh();

#here are some error messages. You need to add location after the error
my $err1 = "cannot get ord. by locate";
my $err2 = "cannot get ord. by refresh; going to use locate";

my $err3 = "cannot cancel order";

my $err4 = "cannot buy";
my $err5 = "cannot sell";

my $err6 = "cannot getMoney";
my $err62 = "cannot get Money portfolio";

my $err7 = "cannot getHoldings";

my $err8 = "cannot refresh lastQuote";


my $lastOrder = "";
my $haveTraded = "";


if ($instrument) {
	$haveTraded = haveTraded($account, $instrument); #this will refresh even if there is no internet	
} else {
	$haveTraded = "";
}


if ($haveTraded) {
	$lastOrder = getLastOrder($rh, $instrument); 	
}
else {
	STDERR->printflush("no last order\n");		
}

my $start = time(); #last order state refresh time
my $id = "";
if ($lastOrder) {
 $id = $lastOrder->id();
}

TAKECOMMANDS:
my $command = "";
while (1) {
	$command = <STDIN>;
	my $raw_response = processOrder($command);
	my $response = join "", $raw_response, "\n";
	($response eq "\n") ? last: STDOUT->printflush("$response"); #it will exit the loop and print BadCommand

}
STDERR->printflush("BadCommand".$command);

my $checked = 1;
sub processOrder {

	my $command = shift;
	my @commandList = split(" ", $command);

	if (!@commandList) {
		STDERR->printflush("blank command in processOrder\n");
		return "";
	}
	if ($command eq "exit\n") {
		STDERR->printflush("exit successful\n");
		exit;
	}
	#print @commandList;
	if ( $commandList[0] eq "getLastOrderState") {
		if (abs (time()-$start) > 4) { #hard coded a timer so you cant spam getLastorderState
    		$lastOrder->refresh(); #if there is a connectin error $lastOrder will turn to null			
			while (!$lastOrder) {
				STDERR->printflush($err2." in getLastorderState\n");
				$lastOrder = $rh->locate_order($id);
			}
	  		$start = time();
    	}
		return $lastOrder->state(); #will only update after the timer period has passed
	}elsif ($commandList[0] eq "cancelLastOrder"){
		$lastOrder->cancel();
		if ($lastOrder){ #
			$lastOrder->refresh(); 
		} else {
			STDERR->printflush($err3."\n");
		}
		while (!$lastOrder) {
			STDERR->printflush($err2." in cancel Last Order\n");
			$lastOrder = $rh->locate_order($id);				
		} 
		$start = time();
		return $lastOrder->state();
	}elsif ($commandList[0] eq "marketBuy"){ #marketBuy should Return the Order
		my $bol = 1;
		$lastOrder = marketBuy($account, $instrument, @commandList);
	    $start = time();
    	return $lastOrder->state();
	}elsif ($commandList[0] eq "marketSell"){ #marketSell should return the order
		$lastOrder = marketSell($account, $instrument, @commandList);
    $start = time();
    return $lastOrder->state();
  }elsif ($commandList[0] eq "limitBuy"){ #return ord
    $lastOrder = "";
    while (!$lastOrder) {
    	try {
    		$lastOrder = limitBuy($account, $instrument, @commandList);
    		$id = $lastOrder->id();
    	} catch {
    		STDERR->printflush($err4." in limit\n");
    	};
    }
    $start = time();
    return $lastOrder->state();    
  }elsif($commandList[0] eq "limitSell"){ #return ord\
    $lastOrder = "";
    while (!$lastOrder) {
    	try {
    		$lastOrder = limitSell($account, $instrument, @commandList);
    		$id = $lastOrder->id();
    	} catch { 
    		STDERR->printflush($err5." in limit\n");
    	};
    }    	
    $start = time();
    return $lastOrder->state();
  }elsif($commandList[0] eq "stopLossBuy"){ #return ord
    $lastOrder = stopLossBuy($account, $instrument, @commandList);
    $start = time();
    return $lastOrder->state();
  }elsif($commandList[0] eq "stopLossSell"){ #return ord
    $lastOrder = stopLossSell($account, $instrument, @commandList);
    $start = time();
    return $lastOrder->state();
  }elsif($commandList[0] eq "getLastOrderInfo"){
    if (abs (time()-$start) > 4) {
		$lastOrder->refresh(); #cost effective yet it could erase the $lastOrder if there is an internet problem
		while (!$lastOrder) {
			STDERR->printflush($err2." in orderInfo\n");			
			$lastOrder = $rh->locate_order($id);
		}
	}
    my $time = $lastOrder->created_at();
    my $side = $lastOrder->side();
    my $price = $lastOrder->price();
    my $state = $lastOrder->state();
	my $volume = $lastOrder->quantity();
    $start = time();
    return $time."\t".$side."\t".$price."\t".$volume."\t".$state;
  } elsif($commandList[0] eq "getMoney"){ #only call this once a day
  	my $money = "";
		my $bol = 0;
		while (!$bol){
			try {
				$account = $rh->accounts()->{results}[0];
				$money = $account->buying_power();
				$bol = 1;
			}catch{ #probs an internet error
				STDERR->printflush($err6."\n")
			};
		}
  		return $money;
  } elsif($commandList[0] eq "getMoneyNet"){ #only call this once a day and it gives you your portfolio withhout uncleared deposits
  	my $money = "";
		my $bol = 0;
		while (!$bol){
			try {
				$account = $rh->accounts()->{results}[0];
				#print Dumper $account;
				my $uncleared = $account->uncleared_deposits();
				$portfolio = $account->portfolio();
				#print Dumper $portfolio;
				$money = $portfolio->{"equity"} - $uncleared + $account->{"max_ach_early_access_amount"};
				$bol = 1;
			}catch{ #probs an internet error
				STDERR->printflush($err62."\n")
			};
		}
  		return $money;
  	} elsif($commandList[0] eq "isTradeable"){
  		if ($instrument){
  				return $instrument->tradeable();
  		}else{
  			return 0;
  		}

	} elsif($commandList[0] eq "haveHoldings") {
		my $bol = 0;
		my $stuff = "undetermined";
		if (!$instrument) {
			return 0;			
		}
		while (!$bol){
			try {
				$account = $rh->accounts()->{results}[0];
				$stuff = haveHoldings($account, $instrument);
				$bol = 1;
			}catch{ #probs an internet error
				STDERR->printflush($err7."\n");
			};
		}
		return $stuff;
	} elsif($commandList[0] eq "price") {
		if (abs (time()-$start2) > 5) {
			$lastQuote->refresh();
			while (!$lastQuote) {
				STDERR->printflush($err8."\n");
				$lastQuote = $instrument->quote(); #this appears to be a O(1) call
				if ($lastQuote) {
					$lastQuote->refresh();
				}
			}
			$start2 = time();
		}		
		return $lastQuote->{raw}->{last_trade_price};
	}elsif ( $commandList[0] eq "filledQuantity") {
		if (abs (time()-$start) > 4) { #hard coded a timer so you cant spam getLastorderState
    		$lastOrder->refresh(); #if there is a connectin error $lastOrder will turn to null			
			while (!$lastOrder) {
				STDERR->printflush($err2." in filledQuantity\n");
				$lastOrder = $rh->locate_order($id);
			}
	  		$start = time();
    	}
		return $lastOrder->cumulative_quantity(); #will only update after the timer period has passed
	} else{
    return "";
  }
}
