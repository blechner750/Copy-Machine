//+------------------------------------------------------------------+
//|                                                 Trade_Sender.mq5 |
//|                                  Copyright 2025, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
input string ServerURL = ""; // Server Endpoint
input int Timeout = 5000;
input double Size_Multiple = 1.0; // Lot Size multiplier

struct TradeMap {
   ulong mt5Ticket;
   string browserTradeID;
   double takeProfit;
   double stopLoss;
};
TradeMap openTrades[];

int OnInit()
  {
   Print("Trader_Sender EA initializing...");
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   
  }
  
//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
    
    int totalPositions = PositionsTotal(); // Get the total number of open positions
    //Print("Current positions: " + totalPositions);
    if (totalPositions == 0 && openTrades.Size() == 0)
    {
        // No trades opened, and tracking nothing
        return;
    }
    else
    { 
      // Either open and/or tracked trades
      
      if(openTrades.Size() > 0)
      {
         // First check if any tracked trades have closed
         CleanupClosedTrades();
         for (int i = 0; i < ArraySize(openTrades); i++)
         {
            // And then check for modifications
            CheckForModifications(openTrades[i].mt5Ticket);
         }
      }
      
      // Now check the open positions are all sent
      for(int i = 0; i < totalPositions; i++)
      {
         ulong ticket = PositionGetTicket(i);
         if(!IsPositionSent(ticket))
            SendRequest_Trade(ticket);   
      }     
    }
  }

//+------------------------------------------------------------------+
//| Function to send new trade                                       |
//+------------------------------------------------------------------+
void SendRequest_Trade(ulong ticket)
{
   if (PositionSelectByTicket(ticket)) // Select the position
   {   
      // Extract position details
      string action = "trade";
      double volume = PositionGetDouble(POSITION_VOLUME) * Size_Multiple;
      double takeProfit = PositionGetDouble(POSITION_TP);
      double stopLoss = PositionGetDouble(POSITION_SL);
      string tradeDirection = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      
      // Prepare JSON data (only include values if they are valid)
      string jsonData = "{\"action\": \"" + action + "\"";
      jsonData += ", \"ticket\": " + (string)ticket;
      jsonData += ", \"direction\": \"" + tradeDirection + "\"";                
      jsonData += ", \"volume\": " + DoubleToString(volume, 5);      
      jsonData += ", \"take_profit\": " + DoubleToString(takeProfit, 5);
      jsonData += ", \"stop_loss\": " + DoubleToString(stopLoss, 5);

      // Close the JSON object
      jsonData += "}";

      Print("Sending position: ", jsonData);

      // Convert JSON string to char array
      uchar jsonDataArray[];
      StringToCharArray(jsonData, jsonDataArray, 0, StringLen(jsonData));

      // Set headers
      string headers = "Content-Type: application/json\r\n";

      // Response buffers
      char result[];
      string resultHeaders = "";

      // Send HTTP POST request
      int responseCode = WebRequest(
         "POST",               // HTTP method
         ServerURL,            // URL
         headers,              // Headers
         Timeout,              // Timeout in milliseconds
         jsonDataArray,        // HTTP message body
         result,               // Server response
         resultHeaders         // Response headers
      );
    
      // Handle the response
      if (responseCode == -1)
      {
         Print("WebRequest failed: ", GetLastError());
      }
      else
      {
         Print("Response code: ", responseCode);
         Print("Server response: ", CharArrayToString(result));
         string browserID;
         ParseJSON(CharArrayToString(result), "", browserID);
         MarkPositionAsSent(ticket, browserID, takeProfit, stopLoss);
      }
   }
}

//+------------------------------------------------------------------+
//| Function to modify existing trade                                |
//+------------------------------------------------------------------+
void SendRequest_Modify(ulong ticket)
{
   if (PositionSelectByTicket(ticket)) // Select position
   {
	  // Pull the trade from the array
      TradeMap entry;
      RetreiveTradeFromMap(ticket, entry);
   
      // Extract position details
      string action = "modify";
      double volume = PositionGetDouble(POSITION_VOLUME) * Size_Multiple;
      double takeProfit = 0.0;
      if(entry.takeProfit != PositionGetDouble(POSITION_TP))
         takeProfit = PositionGetDouble(POSITION_TP);
      double stopLoss = 0.0;
      if(entry.stopLoss != PositionGetDouble(POSITION_SL))
         stopLoss = PositionGetDouble(POSITION_SL);
      string tradeDirection = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      
	  // Set new TP/SL values for array entry
      entry.takeProfit = PositionGetDouble(POSITION_TP);
      entry.stopLoss = PositionGetDouble(POSITION_SL);
      
      // Prepare JSON data
      string jsonData = "{\"action\": \"" + action + "\"";
      jsonData += ", \"ticket\": " + (string)ticket;
      jsonData += ", \"direction\": \"" + tradeDirection + "\"";                  
      jsonData += ", \"volume\": " + DoubleToString(volume, 5); 
      jsonData += ", \"take_profit\": " + DoubleToString(takeProfit, 5);
      jsonData += ", \"stop_loss\": " + DoubleToString(stopLoss, 5);

      // Close the JSON object
      jsonData += "}";

      Print("Sending modification: ", jsonData);

      // Convert JSON string to char array
      uchar jsonDataArray[];
      StringToCharArray(jsonData, jsonDataArray, 0, StringLen(jsonData));

      // Set headers
      string headers = "Content-Type: application/json\r\n";

      // Response buffers
      char result[];
      string resultHeaders = "";

      // Send HTTP POST request
      int responseCode = WebRequest(
         "POST",               // HTTP method
         ServerURL,            // URL
         headers,              // Headers
         Timeout,              // Timeout in milliseconds
         jsonDataArray,        // HTTP message body
         result,               // Server response
         resultHeaders         // Response headers
      );
    
      // Handle the response
      if (responseCode == -1)
      {
         Print("WebRequest failed: ", GetLastError());
      }
      else
      {
         Print("Response code: ", responseCode);
         Print("Server response: ", CharArrayToString(result));
         UpdateMapEntry(ticket, entry); //update array once done
      }
   }
}

//+------------------------------------------------------------------+
//| Function to delete trade from interal dictionary                 |
//+------------------------------------------------------------------+
void SendRequest_Delete(ulong ticket)
{
   string action = "delete";
   double volume = 0.0;
   double takeProfit = 0.0;
   double stopLoss = 0.0;
   string tradeDirection = "NONE";
   // Prepare JSON data (only include values if they are valid)
   string jsonData = "{\"action\": \"" + action + "\"";
   jsonData += ", \"ticket\": " + (string)ticket;
   jsonData += ", \"direction\": \"" + tradeDirection + "\"";                            
   jsonData += ", \"volume\": " + DoubleToString(volume, 5);     
   jsonData += ", \"take_profit\": " + DoubleToString(takeProfit, 5);
   jsonData += ", \"stop_loss\": " + DoubleToString(stopLoss, 5);

   // Close the JSON object
   jsonData += "}";

   Print("Sending position: ", jsonData);

   // Convert JSON string to char array
   uchar jsonDataArray[];
   StringToCharArray(jsonData, jsonDataArray, 0, StringLen(jsonData));

   // Set headers
   string headers = "Content-Type: application/json\r\n";

   // Response buffers
   char result[];
   string resultHeaders = "";
   
   Print("Sending delete: ", jsonData);

   // Send HTTP POST request
   int responseCode = WebRequest(
      "POST",               // HTTP method
      ServerURL,            // URL
      headers,              // Headers
      Timeout,              // Timeout in milliseconds
      jsonDataArray,        // HTTP message body
      result,               // Server response
      resultHeaders         // Response headers
   );
 
   // Handle the response
   if (responseCode == -1)
   {
      Print("WebRequest failed: ", GetLastError());
   }
   else
   {
      Print("Response code: ", responseCode);
      Print("Server response: ", CharArrayToString(result));
   }
}

// Function to check if a position has already been sent
bool IsPositionSent(ulong ticket)
{
   for (int i = 0; i < ArraySize(openTrades); i++)
   {
      if (openTrades[i].mt5Ticket == ticket)
         return true;
   }
   return false;
}

// Function to pull trade from the internal array
void RetreiveTradeFromMap(ulong ticket, TradeMap &entry)
{
   for (int i = 0; i < ArraySize(openTrades); i++)
   {
      if (openTrades[i].mt5Ticket == ticket)
      {
         entry = openTrades[i];
         return;
      }
   }
}

// Function to update array entry
void UpdateMapEntry(ulong ticket, TradeMap &entry)
{
   for (int i = 0; i < ArraySize(openTrades); i++)
   {
      if (openTrades[i].mt5Ticket == ticket)
      {
         openTrades[i] = entry;
         return;
      }
   }
}

// Function to mark a position as sent (add to array)
void MarkPositionAsSent(ulong ticket, string id, double tp, double sl)
{
   TradeMap entry;
   entry.mt5Ticket = ticket;
   entry.browserTradeID = id;
   entry.takeProfit = tp;
   entry.stopLoss = sl;
   
   ArrayResize(openTrades, ArraySize(openTrades) + 1);
   openTrades[ArraySize(openTrades) - 1] = entry;
}


// Helper function to parse JSON response
bool ParseJSON(string jsonString, string key, string &value) {
   int keyPos = StringFind(jsonString, "\"" + key + "\":\"");
   if (keyPos == -1) return false;
   int startPos = keyPos + StringLen(key) + 3;
   int endPos = StringFind(jsonString, "\"", startPos);
   if (endPos == -1) return false;
   value = StringSubstr(jsonString, startPos, endPos - startPos);
   return true;
}


// Function to check and send modified trades
void CheckForModifications(ulong ticket)
{
   if(PositionSelectByTicket(ticket))
   {
      // Get the current take profit and stop loss values
      double currentTakeProfit = PositionGetDouble(POSITION_TP);
      double currentStopLoss = PositionGetDouble(POSITION_SL);
      
      TradeMap entry;
      RetreiveTradeFromMap(ticket, entry);
      
      if(entry.takeProfit != currentTakeProfit || entry.stopLoss != currentStopLoss)
      {
          // If either TP or SL has changed, log the modification and send the updated data
          Print("Trade modified: ", ticket);
          Print("Old TP: ", entry.takeProfit, " -> New TP: ", currentTakeProfit);
          Print("Old SL: ", entry.stopLoss, " -> New SL: ", currentStopLoss);
          
          // Send the updated data
          SendRequest_Modify(ticket);
      }
   }
}

// Function to cleanup any trades in the array that have been closed
void CleanupClosedTrades()
{
    for (int i = ArraySize(openTrades) - 1; i >= 0; i--) // Loop through open trades in reverse
    {
        ulong ticket = openTrades[i].mt5Ticket;
        
        // Check if the trade is still open
        bool isStillOpen = false;
        for (int j = 0; j < PositionsTotal(); j++)
        {
            if (PositionGetTicket(j) == ticket)
            {
                isStillOpen = true;
                break;
            }
        }

        // If the trade is closed, remove it from the array
        if (!isStillOpen)
        {
            Print("Trade closed, removing from tracking: ", ticket);
            ArrayRemove(openTrades, i);
            SendRequest_Delete(ticket);
        }
    }
}